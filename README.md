# OCI Deployment Guide: LangGraph AI Agent

This repository contains the setup and deployment instructions for running a LangGraph-based AI agent on an Oracle Cloud Infrastructure (OCI) compute instance. 

## Prerequisites
* Access to an OCI Compute Instance via SSH.
* Oracle Database Wallet ZIP file (e.g., `Wallet_********.zip`).
* SSH key pair for instance access.
* Required API keys and credentials (Cohere, Database, Langfuse).

---

## 1. Connect to the OCI Instance
SSH into your virtual machine. Replace `<public_ip>` with your actual instance IP.

ssh -i ssh-key opc@<public_ip>


## 2. System Updates & OS Dependencies
Update the system packages and install Python 3.11 along with the required Oracle Instant Client libraries.

sudo dnf update -y

sudo dnf install -y python3.11 python3.11-pip

sudo dnf install -y oracle-instantclient-release-el9

sudo dnf install -y oracle-instantclient19.30-basic

sudo dnf install -y oracle-instantclient19.30-sqlplus

## 3. Project & Virtual Environment Setup
Create a dedicated project directory and initialize a Python virtual environment to isolate your dependencies.

mkdir my_agent

cd my_agent

python3.11 -m venv venv

source venv/bin/activate

## 4. Install Core Python Dependencies
With the virtual environment activated, install the required packages for database connectivity, LangChain, and LangGraph.

pip install oracledb langchain langchain-cohere langchain-community langgraph langgraph-checkpoint-sqlite

## 5. Oracle Database Wallet Configuration
Transfer your Oracle Database wallet from your local machine to the OCI instance to establish the secure database connection.

Run this on your local machine:
(Replace the IP and key name with your actual details)

scp -i ssh-key-2026-02-19.key Wallet_********.zip opc@152.70.125.108:/home/opc/my_agent
