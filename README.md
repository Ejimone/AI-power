# voice agent that sends email, chat with customers, send emails book call with voice

# AI Voice Agent

An AI-powered voice agent that enables users to send emails, chat with customers, and book calls using voice commands. Built with a **FastAPI** backend and a **React** frontend, this project integrates with Gmail API, LiveKit, and configurable STT, TTS, and LLM providers.

## Features

- **Voice Interaction:** Control the agent with voice commands.
- **Email Sending:** Generate and edit emails via a popup, sent using Gmail API.
- **Customer Chat:** Real-time voice-based chat powered by an LLM and TTS.
- **Call Booking:** Initiate and manage calls with LiveKit.
- **Configurable Services:**
  - STT: Switch between ElevenLabs, Cartesia, or Deepgram.
  - TTS: Switch between ElevenLabs, Cartesia, or Deepgram.
  - LLM: Switch between Gemini (default) or OpenAI.

## Architecture

See `architecture.txt` for a detailed breakdown of the system architecture.

## Application Flow

See `appflow.txt` for a step-by-step description of the application flow.

## Project Structure

project-root/
├── backend/
│ ├── app/
│ │ ├── api/
│ │ │ ├── endpoints/
│ │ │ │ ├── voice.py # Voice input processing
│ │ │ │ ├── email.py # Email functionality
│ │ │ │ ├── call.py # Call management
│ │ │ │ └── chat.py # Chat functionality
│ │ │ └── deps.py # API dependencies
│ │ ├── core/
│ │ │ ├── config.py # Configuration for STT, TTS, LLMs
│ │ │ ├── stt.py # STT service integration
│ │ │ ├── tts.py # TTS service integration
│ │ │ ├── llm.py # LLM integration
│ │ │ └── intent.py # Intent recognition logic
│ │ ├── services/
│ │ │ ├── gmail_service.py # Gmail API integration
│ │ │ └── livekit_service.py # LiveKit integration
│ │ └── main.py # FastAPI entry point
│ ├── tests/ # Unit and integration tests
│ └── requirements.txt # Python dependencies
├── frontend/
│ ├── public/ # Static files
│ ├── src/
│ │ ├── components/
│ │ │ ├── VoiceCapture.js # Voice input component
│ │ │ ├── EmailPopup.js # Editable email popup
│ │ │ ├── CallInterface.js # LiveKit call interface
│ │ │ └── ChatInterface.js # Chat interface
│ │ ├── services/
│ │ │ └── api.js # Backend API client
│ │ ├── App.js # Main React component
│ │ └── index.js # React entry point
│ ├── package.json # Node.js dependencies
│ └── .env # Frontend environment variables
├── credentials.json # Gmail API credentials
├── README.md # Project documentation
├── architecture.txt # Architecture details
└── appflow.txt # Application flow details

## Prerequisites

- Python 3.9+ (for backend)
- Node.js 16+ (for frontend)
- Gmail API credentials (`credentials.json`)
- API keys for:
  - ElevenLabs, Cartesia, or Deepgram (STT/TTS)
  - OpenAI or Gemini (LLM)
  - LiveKit (calls)

## Setup Instructions

### 1. Backend Setup

1. Navigate to the `backend/` directory:
2. Install Python dependencies:
3. Configure `app/core/config.py`:

- Add API keys for STT, TTS, LLM, and LiveKit.
- Specify default providers (e.g., Gemini for LLM, ElevenLabs for STT/TTS).

4. Place `credentials.json` in the project root for Gmail API.
5. Start the FastAPI server:
   uvicorn app.main:app --reload

- Runs on `http://localhost:8000` by default.

### 2. Frontend Setup

1. Navigate to the `frontend/` directory:
2. Create a `.env` file in `frontend/`:
   REACT_APP_API_URL=http://localhost:8000

- Runs on `http://localhost:3000` by default.

### 3. Gmail API Configuration

- Obtain `credentials.json` from the Google Cloud Console:

1. Create a project and enable the Gmail API.
2. Set up OAuth 2.0 credentials.
3. Download the credentials file as `credentials.json`.

- Place it in the project root (`project-root/`).
- On first run, authenticate via the browser to generate a token.

## Usage

1. Open the web application at `http://localhost:3000`.
2. Use voice commands to:

- **Send Email:** Say "Send an email to [recipient] about [topic]." Edit the generated email in the popup and confirm.
- **Book Call:** Say "Book a call." The LiveKit interface will activate.
- **Chat:** Say "Chat about [topic]." The agent will respond via voice.

3. Switch providers (e.g., STT, TTS, LLM) by updating `backend/app/core/config.py` and restarting the backend.

## Development Tips

- **Backend:**
- Add new API endpoints in `app/api/endpoints/`.
- Extend service integrations in `app/services/`.
- **Frontend:**
- Add new components in `src/components/`.
- Update API calls in `src/services/api.js`.
- **Testing:**
- Write tests in `backend/tests/` using pytest.

## Troubleshooting

- **CORS Issues:** Ensure FastAPI allows requests from `http://localhost:3000`.
- **API Keys:** Verify all keys in `config.py` are valid.
- **Gmail API:** Re-authenticate if the token expires.

## License

MIT
