# Business Simulation API

FastAPI-based business simulation API that helps users make and analyze business decisions through an AI-powered recommendation system.

## Project Structure

```
AI-agents/
├── api.py                    # main FastAPI application and endpoints
├── simulation_manager.py     # core simulation logic and state management
├── metrics_manager.py        # handles business metrics and their updates
├── SIMULATION_API.md         # API documentation with examples
├── metrics_data.json         # initial metrics and constraints
├── simulation_data.json      # weekly challenges and simulation data
└── requirements.txt          # python dependencies
```

Additional files:
- stage_2.py: Console interface for running the simulation
- autogen.py: first experiment with agentchat
- data_manager.py: tracks and updates metrics in stage_2

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
# Create .env file with:
OPENAI_API_KEY=your_api_key_here
```

3. Start the server:
```bash
python api.py
```

## Key Files

- `api.py`: FastAPI routes for simulation control, decision submission, and actions
- `simulation_manager.py`: Manages simulation state, analyzes decisions using OpenAI API
- `metrics_manager.py`: Tracks and updates business metrics with uncertainty factors
- `SIMULATION_API.md`: Complete API documentation with example 4-week simulation
- `metrics_data.json`: Defines metric constraints and initial values
- `simulation_data.json`: Contains weekly challenges and department contexts

## API Endpoints

- `POST /api/simulation/start`: Start new simulation
- `GET /api/simulation/status`: Get current state
- `POST /api/decisions/submit`: Submit business decision
- `GET /api/decisions/{id}/recommendations`: Get AI recommendations
- `POST /api/decisions/{id}/action`: Take action on recommendations

## Example Usage

```bash
# Start simulation
curl -X POST http://localhost:8000/api/simulation/start

# Submit decision
curl -X POST http://localhost:8000/api/decisions/submit \
  -H "Content-Type: application/json" \
  -d '{"content": "Increase marketing budget by 20%"}'
```

See `SIMULATION_API.md` for complete documentation and example flows.
