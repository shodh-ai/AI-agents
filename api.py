from fastapi import FastAPI, HTTPException
from typing import Dict, List, Any, Optional, Literal
from pydantic import BaseModel
import uvicorn
from simulation_manager import SimulationManager

app = FastAPI(title="Business Simulation API", version="1.0.0")

simulation = SimulationManager()

class Decision(BaseModel):
    content: str

class SimulationStatus(BaseModel):
    current_week: int
    current_department: str
    discussion_started: bool
    is_running: bool
    awaiting_action: bool
    current_decision_id: Optional[str] = None
    challenge: Optional[Dict[str, Any]] = None

class PostAnalysisAction(BaseModel):
    action: Literal["accept_all", "discuss_specific", "request_new", "end_session"]
    specific_recommendations: Optional[List[int]] = None  # For discuss_specific action
    feedback: Optional[str] = None  # For request_new action

class AnalysisResponse(BaseModel):
    decision_id: str
    analysis: Dict[str, Any]
    available_actions: List[str]

class MetricsResponse(BaseModel):
    metrics: Dict[str, Any]

class DecisionResponse(BaseModel):
    decision_id: str
    content: str
    week: int
    analysis: Optional[Dict[str, Any]]

class ActionResponse(BaseModel):
    status: str
    message: str
    current_week: Optional[int] = None
    next_challenge: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    analysis: Optional[Dict[str, Any]] = None

class DiscussionFeedback(BaseModel):
    feedback: str
    specific_recommendations: List[str] = []

class Action(BaseModel):
    action: str
    feedback: Optional[str] = None
    specific_recommendations: Optional[List[str]] = None

@app.get("/")
async def root():
    return {"message": "Business Simulation API"}

@app.post("/api/simulation/start")
async def start_simulation():
    global simulation
    if not hasattr(simulation, 'is_running'):
        simulation.is_running = False
    
    if simulation.is_running:
        raise HTTPException(status_code=400, detail="Simulation is already running")
    
    simulation.is_running = True
    week_key = f"week{simulation.current_week + 1}"
    current_challenge = simulation.simulation_data["weekly_challenges"][week_key]
    
    return {
        "message": "Simulation started successfully",
        "current_week": simulation.current_week + 1,
        "department": simulation.current_department,
        "challenge": current_challenge
    }

@app.get("/api/simulation/status", response_model=SimulationStatus)
async def get_simulation_status():
    if not hasattr(simulation, 'is_running'):
        simulation.is_running = False
    if not hasattr(simulation, 'awaiting_action'):
        simulation.awaiting_action = False
    if not hasattr(simulation, 'current_decision_id'):
        simulation.current_decision_id = None
        
    week_key = f"week{simulation.current_week + 1}"
    current_challenge = simulation.simulation_data["weekly_challenges"][week_key]
    
    return {
        "current_week": simulation.current_week,
        "current_department": simulation.current_department,
        "discussion_started": simulation.discussion_started,
        "is_running": simulation.is_running,
        "awaiting_action": simulation.awaiting_action,
        "current_decision_id": simulation.current_decision_id,
        "challenge": current_challenge
    }

@app.post("/api/simulation/reset")
async def reset_simulation():
    global simulation
    simulation = SimulationManager()
    return {"message": "Simulation reset successfully"}

@app.get("/api/simulation/week/{week_number}")
async def get_week_challenge(week_number: int):
    if week_number < 1 or week_number > len(simulation.simulation_data["weekly_challenges"]):
        raise HTTPException(status_code=404, detail="Week not found")
    
    week_key = f"week{week_number}"
    return simulation.simulation_data["weekly_challenges"][week_key]

@app.get("/api/metrics/current", response_model=MetricsResponse)
async def get_current_metrics():
    return {"metrics": simulation.get_current_metrics()}

@app.get("/api/metrics/week/{week_number}", response_model=MetricsResponse)
async def get_week_metrics(week_number: int):
    if week_number < 1 or week_number > simulation.current_week + 1:
        raise HTTPException(status_code=404, detail="Week metrics not found")
    return {"metrics": simulation.metrics_manager.get_week_metrics(week_number)}

@app.post("/api/decisions/submit", response_model=AnalysisResponse)
async def submit_decision(decision: Decision):
    if not decision.content.strip():
        raise HTTPException(status_code=400, detail="Decision content cannot be empty")
    
    if not simulation.is_running:
        raise HTTPException(status_code=400, detail="Simulation is not running. Please start it first.")
    
    if hasattr(simulation, 'awaiting_action') and simulation.awaiting_action:
        raise HTTPException(
            status_code=400, 
            detail="Previous decision needs action. Use /api/decisions/{decision_id}/action first."
        )
    
    # analyze the decision using the simulation manager's API-specific method
    analysis_result = await simulation.analyze_user_decision_api(decision.content)
    
    if "error" in analysis_result:
        raise HTTPException(status_code=400, detail=analysis_result["error"])
    
    # store the decision
    decision_id = f"decision_{simulation.current_week + 1}"
    simulation.user_decisions.append({
        "id": decision_id,
        "content": decision.content,
        "week": simulation.current_week + 1,
        "analysis": analysis_result,
        "status": "pending_action"
    })
    
    # set simulation state to await action
    simulation.awaiting_action = True
    simulation.current_decision_id = decision_id
    
    return {
        "decision_id": decision_id,
        "analysis": analysis_result,
        "available_actions": [
            "accept_all",
            "discuss_specific",
            "request_new",
            "end_session"
        ]
    }

@app.get("/api/decisions/history")
async def get_decision_history():
    return {"decisions": simulation.user_decisions}

@app.get("/api/resources/available")
async def get_available_resources():
    week_key = f"week{simulation.current_week + 1}"
    return {
        "resources": simulation.simulation_data["weekly_challenges"][week_key]["available_resources"]
    }

@app.get("/api/resources/constraints")
async def get_constraints():
    week_key = f"week{simulation.current_week + 1}"
    return {
        "constraints": simulation.simulation_data["weekly_challenges"][week_key]["constraints"]
    }

@app.post("/api/decisions/{decision_id}/action", response_model=ActionResponse)
async def handle_decision_action(decision_id: str, action: Action):
    if not simulation.is_running:
        raise HTTPException(status_code=400, detail="Simulation is not running")
        
    if not simulation.awaiting_action:
        raise HTTPException(status_code=400, detail="No pending decision action")
        
    if decision_id != simulation.current_decision_id:
        raise HTTPException(status_code=400, detail="Invalid decision ID")
    
    # find the current decision
    decision = next((d for d in simulation.user_decisions if d["id"] == decision_id), None)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    # handle the action
    if action.action == "accept_all":
        simulation.awaiting_action = False
        next_week_state = simulation.advance_week()
        
        if "error" in next_week_state:
            raise HTTPException(status_code=400, detail=next_week_state["error"])
        response = {
            "status": next_week_state["status"],
            "message": f"Decision accepted and implemented (recommendations version {decision.get('recommendations_version', 1)})",
            "current_week": next_week_state["current_week"],
            "metrics": next_week_state.get("metrics", next_week_state.get("final_metrics", {}))
        }
        
        if next_week_state["status"] == "in_progress":
            response["next_challenge"] = next_week_state["next_challenge"]
            
        return response
        
    elif action.action == "discuss_specific":
        if not action.specific_recommendations:
            raise HTTPException(
                status_code=400,
                detail="Must specify recommendations to discuss in specific_recommendations"
            )
            
        if not action.feedback:
            raise HTTPException(
                status_code=400,
                detail="Must provide feedback for discussion"
            )
            
        # get new analysis based on specific feedback
        new_analysis = await simulation.analyze_user_decision_api(
            decision["content"],
            feedback=action.feedback,
            specific_recommendations=action.specific_recommendations
        )
        
        decision["analysis"] = new_analysis
        decision["recommendations_version"] = simulation.current_recommendations_version
        
        return {
            "status": "discussing",
            "message": f"Discussing specific recommendations (version {decision.get('recommendations_version', 1)})",
            "current_week": simulation.current_week + 1,
            "metrics": simulation.get_current_metrics(),
            "next_challenge": simulation.get_current_challenge(),
            "analysis": new_analysis
        }
        
    elif action.action == "request_new":
        new_analysis = await simulation.analyze_user_decision_api(
            decision["content"],
            feedback=action.feedback if action.feedback else None
        )
        
        decision["analysis"] = new_analysis
        decision["recommendations_version"] = simulation.current_recommendations_version
        
        return {
            "status": "new_recommendations",
            "message": f"New recommendations generated (version {simulation.current_recommendations_version})",
            "current_week": simulation.current_week + 1,
            "metrics": simulation.get_current_metrics(),
            "next_challenge": simulation.get_current_challenge(),
            "analysis": new_analysis
        }
        
    elif action.action == "end_session":
        simulation.is_running = False
        return {
            "status": "completed",
            "message": "Simulation ended by user",
            "current_week": simulation.current_week + 1,
            "metrics": simulation.get_current_metrics()
        }
    
    raise HTTPException(status_code=400, detail="Invalid action")

@app.get("/api/decisions/{decision_id}/recommendations")
async def get_recommendations(decision_id: str):
    decision = next((d for d in simulation.user_decisions if d["id"] == decision_id), None)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    return {
        "decision_id": decision_id,
        "recommendations": decision["analysis"].get("implementation_strategy", {}).get("steps", [])
    }

@app.get("/api/simulation/status")
async def get_simulation_status():
    if not simulation.is_running:
        return {
            "status": "not_running",
            "message": "Simulation is not running"
        }
        
    current_metrics = simulation.get_current_metrics()
    current_challenge = simulation.get_current_challenge()
    
    return {
        "status": "in_progress" if simulation.is_running else "completed",
        "current_week": simulation.current_week + 1,
        "awaiting_action": simulation.awaiting_action,
        "current_decision_id": simulation.current_decision_id if simulation.awaiting_action else None,
        "metrics": current_metrics,
        "current_challenge": current_challenge
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
