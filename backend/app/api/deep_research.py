
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User as UserModel
from app.schemas.deep_research import DeepResearchRequest, DeepResearchResponse
from app.schemas.chat import MessageCreate
from app.services.deep_research_service import DeepResearchService
from app.services.chat_service import ChatService

router = APIRouter()

@router.post("/", response_model=DeepResearchResponse)
async def run_deep_research(
    request: DeepResearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Initiates a deep research task for the given query.
    """
    if not request.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        # Run the deep research
        report = await DeepResearchService.run_deep_research(
            query=request.query,
            max_concurrent_research_units=request.max_concurrent_research_units,
            max_researcher_iterations=request.max_researcher_iterations,
            max_react_tool_calls=request.max_react_tool_calls,
            max_structured_output_retries=request.max_structured_output_retries
        )
        
        # Save messages to database if chat_id is provided
        if request.chat_id:
            try:
                # Verify the chat exists and user has access
                chat = await ChatService.get_chat(db, request.chat_id, current_user.id)
                if not chat:
                    raise HTTPException(status_code=404, detail="Chat not found")
                
                # Save user message
                user_message = MessageCreate(
                    content=request.query,
                    role="user"
                )
                await ChatService.add_message(db, request.chat_id, user_message)
                
                # Save assistant message
                assistant_message = MessageCreate(
                    content=report,
                    role="assistant"
                )
                await ChatService.add_message(db, request.chat_id, assistant_message)
                
            except HTTPException:
                # Re-raise HTTP exceptions (like chat not found)
                raise
            except Exception as save_error:
                # Log but don't fail the request if message saving fails
                print(f"Warning: Failed to save deep research messages: {save_error}")
        
        return DeepResearchResponse(report=report)
    except Exception as e:
        # Log the exception details for debugging
        print(f"Error during deep research: {e}")
        raise HTTPException(status_code=500, detail="An error occurred during the research process.")
