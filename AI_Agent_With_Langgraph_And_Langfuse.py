import os
import sqlite3
import oracledb
from typing import TypedDict, Literal
from langchain_cohere import ChatCohere
from langchain_community.utilities import SQLDatabase
from langgraph.graph import StateGraph, END
from langfuse.langchain import CallbackHandler
from langfuse import observe, get_client, propagate_attributes
import time
from langgraph.checkpoint.sqlite import SqliteSaver

# ==========================================
# 1. SETUP (Standard Config)
# ==========================================
os.environ["COHERE_API_KEY"] = os.environ["COHERE_API_KEY"]
DB_USER = "ADMIN" 
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_DSN = "iawbf4imgo7zddqt_high" 
WALLET_PATH = os.path.join(os.getcwd(), 'wallet')
WALLET_PASSWORD = os.environ["WALLET_PASSWORD"]

db_file = "demo_checkpoints.sqlite"
if os.path.exists(db_file):
    os.remove(db_file)
    print(f" [Demo Prep] Deleted old '{db_file}' to start fresh.")

if 'client_initialized' not in globals():
    oracledb.init_oracle_client(config_dir=WALLET_PATH)
    globals()['client_initialized'] = True

db = SQLDatabase.from_uri(
    f"oracle+oracledb://{DB_USER}:{DB_PASSWORD}@",
    schema="SH",
    engine_args={"connect_args": {"dsn": DB_DSN, "wallet_location": WALLET_PATH, "wallet_password": WALLET_PASSWORD}}
)

llm = ChatCohere(model="command-r-plus-08-2024", temperature=0)

# ==========================================
# 2. STATE DEFINITION 
# ==========================================
class AgentState(TypedDict):
    question: str
    schema_info: str
    sql_query: str
    db_result: str
    error: str  
    answer: str
    retry_count: int 

SYSTEM_PREAMBLE = "You are an Oracle SQL Expert for the SH schema. You have permission to query. Do not prefix tables with SH."

# ==========================================
# 3. NODES
# ==========================================
def get_schema(state: AgentState):
    return {"schema_info": db.get_table_info(), "retry_count": 0, "error": None}

def generate_sql(state: AgentState):
    error_context = ""
    if state.get("error"):
        print(f" Retrying... Previous Error: {state['error']}")
        error_context = f"\n\nPREVIOUS ERROR: {state['error']}\nINSTRUCTION: Fix the SQL to avoid this error. Check table definitions carefully."

    prompt = SYSTEM_PREAMBLE + "\n\n"
    prompt += "Schema: " + str(state['schema_info']) + "\n"
    prompt += "Question: " + str(state['question']) + error_context + "\n\n"
    prompt += "Rule: Return ONLY SQL. No markdown. No semicolon. Generate the SQL with proper aliases so that we do not get Ambiguous column names error.\nSQL:"
   
    response = llm.invoke(prompt).content.strip()
    sql = response.replace("```sql", "").replace("```", "").strip()
    if sql.endswith(";"): sql = sql[:-1]
    
    return {"sql_query": sql, "retry_count": state.get("retry_count", 0)}

def execute_sql(state: AgentState):
    try:
        db.run("ALTER SESSION SET CURRENT_SCHEMA = SH")
        result = db.run(state['sql_query'])
        return {"db_result": str(result), "error": None}
    except Exception as e:
        return {"error": str(e), "retry_count": state["retry_count"] + 1}

def finalize_answer(state: AgentState):
    prompt = (
        "You are a data analyst. Provide a clear, natural language answer to the user's question "
        "using ONLY the following database results.\n\n"
        f"User Question: {state['question']}\n"
        f"Database Result: {state['db_result']}\n\n"
        "Final Answer:"
    )
    response = llm.invoke(prompt).content
    return {"answer": response}

# ==========================================
# 4. CONDITIONAL LOGIC ( The "Router" )
# ==========================================
def should_continue(state: AgentState) -> Literal["generate_sql", "finalize_answer"]:
    if state["error"]:
        if state["retry_count"] < 3:
            return "generate_sql"  
        else:
            return "finalize_answer" 
    return "finalize_answer"

# ==========================================
# 5. BUILD GRAPH
# ==========================================
workflow = StateGraph(AgentState)

workflow.add_node("get_schema", get_schema)
workflow.add_node("generate_sql", generate_sql)
workflow.add_node("execute_sql", execute_sql)
workflow.add_node("finalize_answer", finalize_answer)

workflow.set_entry_point("get_schema")
workflow.add_edge("get_schema", "generate_sql")
workflow.add_edge("generate_sql", "execute_sql")

workflow.add_conditional_edges("execute_sql", should_continue)
workflow.add_edge("finalize_answer", END)

conn = sqlite3.connect(db_file, check_same_thread=False)
memory = SqliteSaver(conn)

app = workflow.compile(checkpointer=memory)

# ==========================================
# 6. RUN BATCH (File I/O)
# ==========================================
input_file = "questions.txt"
output_file = "answers.txt"

try:
    with open(input_file, "r") as f:
        questions = [line.strip() for line in f.readlines() if line.strip()]
except FileNotFoundError:
    print(f" Error: '{input_file}' not found. Please create it first.")
    exit()

@observe(name="AI_Agent_Answer_Question_using_SQL")
def process_question(q, index):
    
    langfuse_handler = CallbackHandler()
    
    inputs = {"question": q}
    thread_config = {
        "configurable": {"thread_id": f"batch_question_{index}"},
        "callbacks": [langfuse_handler] # Attach the handler here
    }
    
    final_answer_text = "Error: Failed to generate answer."
    
    # 1. Run your stream
    for output in app.stream(inputs, config=thread_config):
        for key, value in output.items():
            if key == 'finalize_answer':
                final_answer_text = value['answer']
                print(f"\n FINAL ANSWER:\n{final_answer_text}")
            elif key == 'execute_sql' and value.get("error"):
                print(f" Execution Failed: {value['error']}")
            elif key == 'generate_sql':
                sql_query = value.get("sql_query")
                print(f" Generated SQL : {sql_query}")
            elif key == 'get_schema':
                print(" Fetching Schema...")
                
    return final_answer_text


print(" Self-Correcting Agent Starting...")
print("-" * 70)

with open(output_file, "w") as out_f:
    
    for index, q in enumerate(questions, 1):
        print(f"\n Processing [{index}/{len(questions)}]: {q}")
        print("-" * 50)
        
        try:
            final_answer = process_question(q, index)
            get_client().flush()

        except Exception as e:
            print(f" Graph Error: {e}")
            final_answer_text = f"Graph Error: {e}"
            
        out_f.write(f"Question {index}: {q}\n")
        out_f.write(f"Answer:\n{final_answer}\n")
        out_f.write("-" * 50 + "\n\n")
            
        time.sleep(1)

print(f"\n Batch processing complete. Results saved to {output_file}")
