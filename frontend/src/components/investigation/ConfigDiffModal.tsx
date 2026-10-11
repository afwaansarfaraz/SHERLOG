import React, { useState } from "react"
import { X, Code2, Copy, Check } from "lucide-react"
import { Button } from "../common/Button"

interface ConfigDiffModalProps {
  isOpen: boolean
  onClose: () => void
  diff: string
  serviceName: string
}

export const ConfigDiffModal: React.FC<ConfigDiffModalProps> = ({
  isOpen,
  onClose,
  diff,
  serviceName,
}) => {
  const [copied, setCopied] = useState(false)

  if (!isOpen) return null

  const handleCopy = () => {
    navigator.clipboard.writeText(diff)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const lines = diff.split("\n")

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className="w-full max-w-2xl bg-soot border border-ash rounded-lg shadow-2xl overflow-hidden flex flex-col max-h-[80vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-ash bg-ink/50">
          <div className="flex items-center gap-2">
            <Code2 className="w-4 h-4 text-amber" />
            <span className="font-semibold text-xs text-bone tracking-wide">
              Proposed Configuration Diff — {serviceName}
            </span>
          </div>
          <button
            onClick={onClose}
            aria-label="Close diff modal"
            className="text-dust hover:text-bone p-1 rounded hover:bg-soot transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Diff Content */}
        <div className="p-4 overflow-y-auto font-mono text-xs bg-ink/90 flex-1 divide-y divide-ash/20 custom-scrollbar">
          {lines.map((line, idx) => {
            const isAdded = line.startsWith("+") && !line.startsWith("+++")
            const isRemoved = line.startsWith("-") && !line.startsWith("---")
            const isHeader =
              line.startsWith("@@") || line.startsWith("---") || line.startsWith("+++")

            return (
              <div
                key={idx}
                className={`py-0.5 px-2 select-text flex items-start gap-3 ${
                  isAdded
                    ? "bg-[#162722] text-verdigris"
                    : isRemoved
                      ? "bg-[#2E1517] text-vermilion"
                      : isHeader
                        ? "text-dust font-bold"
                        : "text-bone/80"
                }`}
              >
                <span className="text-dust/50 select-none text-[10px] w-6 text-right shrink-0">
                  {idx + 1}
                </span>
                <span className="whitespace-pre flex-1 overflow-x-auto custom-scrollbar">{line}</span>
              </div>
            )
          })}
        </div>

        {/* Footer */}
        <div className="p-3 bg-ink/70 border-t border-ash flex items-center justify-between text-xs">
          <Button variant="ghost" size="sm" onClick={handleCopy}>
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-verdigris mr-1" />
                <span className="text-verdigris">Copied to clipboard</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 mr-1" />
                <span>Copy Diff</span>
              </>
            )}
          </Button>
          <Button variant="secondary" size="sm" onClick={onClose}>
            Done
          </Button>
        </div>
      </div>
    </div>
  )
}
