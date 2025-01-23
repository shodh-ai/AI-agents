# Business Simulation API Documentation

# Start Simulation

## Endpoint

`POST /api/simulation/start`

## Description

Initializes a new business simulation session. This endpoint sets up the initial state, metrics, and challenges for the simulation.

## Request

- **URL Parameters**: None
- **Headers**:
  - `Content-Type: application/json`
- **Body**: Empty

### Request Format

```json
{}
```

## Response

- `status` (string): Current status of the simulation ("started")
- `current_week` (integer): The current week number (starts at 1)
- `metrics` (object): Initial business metrics
  - `core` (object): Core business metrics
    - `revenue` (float)
    - `profit_margin` (float)
    - `customer_satisfaction` (float)
    - `employee_satisfaction` (float)
  - `department` (object): Department-specific metrics
    - `operational_efficiency` (float)
    - `sales_growth` (float)
    - `innovation_index` (float)
- `next_challenge` (object): Details of the first week's challenge
  - `department` (string): Department responsible for the challenge
  - `description` (string): Description of the challenge
  - `context` (string): Additional context about the situation

### Response Format

```json
{
  "status": "string",
  "current_week": "integer",
  "metrics": {
    "core": {
      "revenue": "float",
      "profit_margin": "float",
      "customer_satisfaction": "float",
      "employee_satisfaction": "float"
    },
    "department": {
      "operational_efficiency": "float",
      "sales_growth": "float",
      "innovation_index": "float"
    }
  },
  "next_challenge": {
    "department": "string",
    "description": "string",
    "context": "string"
  }
}
```

# Get Simulation Status

## Endpoint

`GET /api/simulation/status`

## Description

Retrieves the current state of the simulation, including week number, metrics, and current challenge.

## Request

- **URL Parameters**: None
- **Headers**: None
- **Body**: None

## Response

Same format as the start simulation response, with additional `is_running` field.

### Response Format

```json
{
  "status": "string",
  "is_running": "boolean",
  "current_week": "integer",
  "metrics": {
    "core": {
      "revenue": "float",
      "profit_margin": "float",
      "customer_satisfaction": "float",
      "employee_satisfaction": "float"
    },
    "department": {
      "operational_efficiency": "float",
      "sales_growth": "float",
      "innovation_index": "float"
    }
  },
  "next_challenge": {
    "department": "string",
    "description": "string",
    "context": "string"
  }
}
```

# Submit Decision

## Endpoint

`POST /api/decisions/submit`

## Description

Submits a business decision for the current week's challenge. The decision will be analyzed and recommendations will be generated.

## Request

- **URL Parameters**: None
- **Headers**:
  - `Content-Type: application/json`
- **Body**:
  - `content` (string): The decision text describing the action to be taken

### Request Format

```json
{
  "content": "string"
}
```

## Response

- `decision_id` (string): Unique identifier for the submitted decision
- `analysis` (object): AI analysis of the decision
  - `strengths` (array): List of decision strengths
  - `weaknesses` (array): List of potential weaknesses
  - `recommendations` (array): List of recommended actions
    - `action` (string): Recommended action
    - `rationale` (string): Explanation for the recommendation
    - `metric_impacts` (array): Expected impact on metrics
      - `metric` (string): Name of the metric
      - `change` (float): Expected percentage change
- `status` (string): Status of the decision ("pending_action")

### Response Format

```json
{
  "decision_id": "string",
  "analysis": {
    "strengths": ["string"],
    "weaknesses": ["string"],
    "recommendations": [
      {
        "action": "string",
        "rationale": "string",
        "metric_impacts": [
          {
            "metric": "string",
            "change": "float"
          }
        ]
      }
    ]
  },
  "status": "string"
}
```

# Get Decision Recommendations

## Endpoint

`GET /api/decisions/{decision_id}/recommendations`

## Description

Retrieves the AI-generated recommendations for a specific decision.

## Request

- **URL Parameters**:
  - `decision_id` (string): ID of the decision
- **Headers**: None
- **Body**: None

## Response

Same format as the analysis object in the submit decision response.

### Response Format

```json
{
  "strengths": ["string"],
  "weaknesses": ["string"],
  "recommendations": [
    {
      "action": "string",
      "rationale": "string",
      "metric_impacts": [
        {
          "metric": "string",
          "change": "float"
        }
      ]
    }
  ]
}
```

# Take Action on Decision

## Endpoint

`POST /api/decisions/{decision_id}/action`

## Description

Takes action on a decision's recommendations. Actions can be: accepting all recommendations, discussing specific ones, requesting new recommendations, or ending the session.

## Request

- **URL Parameters**:
  - `decision_id` (string): ID of the decision
- **Headers**:
  - `Content-Type: application/json`
- **Body**:
  - `action` (string): Type of action ("accept_all", "discuss_specific", "request_new", or "end_session")
  - `feedback` (string, optional): Feedback when discussing specific recommendations
  - `specific_recommendations` (array of strings, optional): List of specific recommendations to discuss

### Request Format

```json
{
  "action": "string",
  "feedback": "string",
  "specific_recommendations": ["string"]
}
```

## Response

- `status` (string): New status after the action
- `message` (string): Description of what happened
- `current_week` (integer): Current week number
- `metrics` (object): Updated metrics after the action
- `next_challenge` (object): Next week's challenge (if applicable)
- `analysis` (object, optional): New analysis if recommendations were discussed

### Response Format

```json
{
  "status": "string",
  "message": "string",
  "current_week": "integer",
  "metrics": {
    "core": {
      "revenue": "float",
      "profit_margin": "float",
      "customer_satisfaction": "float",
      "employee_satisfaction": "float"
    },
    "department": {
      "operational_efficiency": "float",
      "sales_growth": "float",
      "innovation_index": "float"
    }
  },
  "next_challenge": {
    "department": "string",
    "description": "string",
    "context": "string"
  },
  "analysis": {
    "strengths": ["string"],
    "weaknesses": ["string"],
    "recommendations": [
      {
        "action": "string",
        "rationale": "string",
        "metric_impacts": [
          {
            "metric": "string",
            "change": "float"
          }
        ]
      }
    ]
  }
}
```

# Error Responses

All endpoints may return the following error responses:

- **400 Bad Request**: Invalid input or request
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server-side error

### Error Response Format

```json
{
  "detail": "string"
}
```

# Simulation Flow

1. **Start Simulation**
   - Call `POST /api/simulation/start`
   - Receive initial state and first challenge

2. **For Each Week**:
   a. **Submit Decision**
      - Call `POST /api/decisions/submit`
      - Receive decision analysis and recommendations
   
   b. **Review Recommendations**
      - Optionally call `GET /api/decisions/{decision_id}/recommendations`
      - Review the AI analysis and recommendations
   
   c. **Take Action**
      - Call `POST /api/decisions/{decision_id}/action`
      - Choose one of:
        - Accept all recommendations
        - Discuss specific recommendations
        - Request new recommendations
        - End session
      - Receive updated state and next challenge

3. **Monitor Progress**
   - Call `GET /api/simulation/status` at any time
   - Track metrics and current state

4. **End Simulation**
   - Call `POST /api/decisions/{decision_id}/action` with "end_session"
   - Receive final metrics and summary

# Example 4-Week Simulation

This section demonstrates a complete 4-week simulation with example API calls and responses.

## Week 1: Marketing Challenge

### 1. Start Simulation

```bash
curl -X POST http://localhost:8000/api/simulation/start
```

Response:
```json
{
  "status": "started",
  "current_week": 1,
  "metrics": {
    "core": {
      "revenue": 1000000,
      "profit_margin": 15.5,
      "customer_satisfaction": 85.0,
      "employee_satisfaction": 78.0
    },
    "department": {
      "operational_efficiency": 82.0,
      "sales_growth": 5.2,
      "innovation_index": 72.0
    }
  },
  "next_challenge": {
    "department": "Marketing",
    "description": "Market share is declining due to new competitor entry",
    "context": "A new competitor has entered the market with aggressive pricing..."
  }
}
```

### 2. Submit Decision

```bash
curl -X POST http://localhost:8000/api/decisions/submit \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Increase marketing budget by 20% and focus on digital channels to counter competitor"
  }'
```

Response:
```json
{
  "decision_id": "decision_1",
  "analysis": {
    "strengths": [
      "Quick response to competitive threat",
      "Focus on growing digital presence"
    ],
    "weaknesses": [
      "Significant budget increase might affect short-term profitability"
    ],
    "recommendations": [
      {
        "action": "Implement targeted social media campaign",
        "rationale": "Higher ROI than traditional channels",
        "metric_impacts": [
          {
            "metric": "core.revenue",
            "change": 8.5
          },
          {
            "metric": "core.profit_margin",
            "change": -2.0
          }
        ]
      }
    ]
  },
  "status": "pending_action"
}
```

### 3. Accept Recommendations

```bash
curl -X POST http://localhost:8000/api/decisions/decision_1/action \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accept_all"
  }'
```

## Week 2: Operations Challenge

### 1. check status

```bash
curl http://localhost:8000/api/simulation/status
```

Response:
```json
{
  "status": "in_progress",
  "current_week": 2,
  "metrics": {
    "core": {
      "revenue": 1085000,
      "profit_margin": 13.5,
      "customer_satisfaction": 87.0,
      "employee_satisfaction": 78.0
    },
    "department": {
      "operational_efficiency": 81.0,
      "sales_growth": 8.5,
      "innovation_index": 72.0
    }
  },
  "next_challenge": {
    "department": "Operations",
    "description": "Supply chain disruptions causing delivery delays",
    "context": "Recent global events have disrupted our main supply routes..."
  }
}
```

### 2. submit decision

```bash
curl -X POST http://localhost:8000/api/decisions/submit \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Diversify supplier base and implement real-time inventory tracking"
  }'
```

### 3. discuss specific recommendations

```bash
curl -X POST http://localhost:8000/api/decisions/decision_2/action \
  -H "Content-Type: application/json" \
  -d '{
    "action": "discuss_specific",
    "feedback": "Concerned about implementation time for new inventory system",
    "specific_recommendations": [
      "Implement real-time tracking",
      "Supplier diversification timeline"
    ]
  }'
```

### 4. accept new recommendations

```bash
curl -X POST http://localhost:8000/api/decisions/decision_2/action \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accept_all"
  }'
```

## Week 3: HR Challenge

### 1. submit decision

```bash
curl -X POST http://localhost:8000/api/decisions/submit \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Implement remote work policy and increase training budget"
  }'
```

### 2. request new recommendations

```bash
curl -X POST http://localhost:8000/api/decisions/decision_3/action \
  -H "Content-Type: application/json" \
  -d '{
    "action": "request_new",
    "feedback": "Need more focus on employee retention"
  }'
```

### 3. accept new recommendations

```bash
curl -X POST http://localhost:8000/api/decisions/decision_3/action \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accept_all"
  }'
```

## Week 4: Finance Challenge

### 1. submit decision

```bash
curl -X POST http://localhost:8000/api/decisions/submit \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Restructure debt and invest in automation"
  }'
```

### 2. view recommendations

```bash
curl http://localhost:8000/api/decisions/decision_4/recommendations
```

### 3. end simulation

```bash
curl -X POST http://localhost:8000/api/decisions/decision_4/action \
  -H "Content-Type: application/json" \
  -d '{
    "action": "end_session"
  }'
```

Response:
```json
{
  "status": "completed",
  "message": "Simulation ended by user",
  "current_week": 4,
  "metrics": {
    "core": {
      "revenue": 1250000,
      "profit_margin": 16.5,
      "customer_satisfaction": 89.0,
      "employee_satisfaction": 85.0
    },
    "department": {
      "operational_efficiency": 88.0,
      "sales_growth": 12.5,
      "innovation_index": 78.0
    }
  }
}
```

