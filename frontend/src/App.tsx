import { Chat } from "./components/Chat";
import "./App.css";

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>AI Workflow Builder</h1>
        <p className="subtitle">Tracer bullet — hardcoded workflow (system prompt + calculator)</p>
      </header>
      <Chat />
    </div>
  );
}

export default App;
