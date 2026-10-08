# Chat Service API Documentation

Encapsulates conversational state, multi-issue decomposition, evidence routing, and Streamlit session integration.

```python
from app.chat_service import ChatService

service = ChatService()
result = service.generate_answer(
    conversation_id="conv-123",
    user_query="Bị công ty trừ 50% tiền lương do làm vỡ cốc có đúng luật không?",
    attachment_text=None
)
print(result.answer)
print(result.citations)
```
