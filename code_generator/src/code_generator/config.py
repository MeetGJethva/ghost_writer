"""
config.py – Single LLM configuration point.

To switch LLMs, only change this file.
Supported options (examples):
  - ChatGroq(model="llama3-70b-8192")          # Groq / LLaMA3
  - ChatGroq(model="mixtral-8x7b-32768")       # Groq / Mixtral
  - ChatOpenAI(model="gpt-4o")                 # OpenAI
  - ChatAnthropic(model="claude-3-opus-20240229")  # Anthropic
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

load_dotenv()

# ── LLM CONFIGURATION ─────────────────────────────────────────────────────────
# Change this block to swap the LLM used by ALL agents in the system.

def get_llm(temperature: float = 0):
  """Return the configured LLM instance."""
  return ChatGroq(
      model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
      temperature=temperature,
      api_key=os.getenv("GROQ_API_KEY"),
  )

def code_generator_llm(temperature: float = 0):
  return ChatOpenAI(
    model=os.getenv("CODE_GENERATION_MODEL", "arcee-ai/trinity-large-preview:free"),
    openai_api_key=os.environ.get("OPENROUTER_API_KEY"),
    openai_api_base="https://openrouter.ai/api/v1",
    temperature=temperature,
  )

# ── AGENT SETTINGS ─────────────────────────────────────────────────────────────
# Max iterations each ReAct agent is allowed to run before giving up.
MAX_AGENT_ITERATIONS = int(os.getenv("MAX_AGENT_ITERATIONS", "20"))

# Working directory where generated code will be written.
DEFAULT_OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")
