To create a oci where you can run this code, please do the following 

ssh into vm instance 

ssh -i ssh-key opc@<public_ip>

sudo dnf update -y

sudo dnf install -y python3.11 python3.11-pip

sudo dnf install -y oracle-instantclient-release-el9

sudo dnf install -y oracle-instantclient19.30-basic

sudo dnf install -y oracle-instantclient19.30-sqlplus

mkdir my_agent

cd my_agent

python3.11 -m venv venv

source venv/bin/activate

pip install oracledb langchain langchain-cohere langchain-community langgraph langgraph-checkpoint-sqlite

Download the wallet zip file for your oracle datalake house and upload it to you my_agent dir 

scp -i ssh-key-2026-02-19.key Wallet_********.zip opc@152.70.125.108:/home/opc/my_agent

mkdir wallet

unzip Wallet_*****.zip -d wallet

vi wallet/sqlnet.ora

Change — Directory to /home/opc/my_agent/wallet

Now to download 2 files from https://github.com/athangamani/agentic_ai_with_langgraph.git





To run your python file

export COHERE_API_KEY="******" 

export DB_PASSWORD="******" 

export WALLET_PASSWORD="******"

export LANGFUSE_PUBLIC_KEY="******"

export LANGFUSE_SECRET_KEY="******"

export LANGFUSE_HOST="https://us.cloud.langfuse.com"
