import { ShieldCheck, Terminal, Activity } from "lucide-react"

export function App() {
  return (
    <div className="min-h-screen bg-ink text-bone flex flex-col items-center justify-center p-6 selection:bg-ash selection:text-bone">
      <div className="max-w-md w-full bg-soot border border-ash rounded-lg p-6 space-y-4">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded bg-ink border border-ash flex items-center justify-center text-amber">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <h1 className="font-semibold text-bone text-base tracking-wide">SHERLOG</h1>
            <p className="text-xs text-dust tracking-wider uppercase font-mono">
              AI Incident Investigation Platform
            </p>
          </div>
        </div>

        <div className="border-t border-ash pt-4 space-y-2">
          <div className="flex items-center text-xs text-dust font-mono space-x-2">
            <ShieldCheck className="w-4 h-4 text-verdigris" />
            <span>Environment Initialized</span>
          </div>
          <div className="flex items-center text-xs text-dust font-mono space-x-2">
            <Terminal className="w-4 h-4 text-slate" />
            <span>Case File Palette Configured</span>
          </div>
        </div>

        <div className="pt-2">
          <p className="text-xs text-dust">Awaiting feature implementation approval.</p>
        </div>
      </div>
    </div>
  )
}

export default App
