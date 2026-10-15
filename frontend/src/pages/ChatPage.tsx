import ChatPanel from "../components/chat/ChatPanel";

export default function ChatPage() {
  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-1 text-xl font-semibold text-primary">Analyst chat</h1>
      <p className="mb-4 text-sm text-secondary">
        Conversational access to the registered pipeline datasets. Answers cite their provenance;
        observed, derived and synthetic data are distinguished. Research prototype - not investment,
        credit or underwriting advice.
      </p>
      <div className="h-[28rem]">
        <ChatPanel />
      </div>
    </div>
  );
}
