import React from "react"
import type { Hypothesis, HypothesisLikelihood } from "../../types"

interface HypothesesListProps {
  hypotheses: Hypothesis[]
  selectedHypothesisId?: string
  onSelectHypothesis?: (id: string) => void
}

export const HypothesesList: React.FC<HypothesesListProps> = ({
  hypotheses,
  selectedHypothesisId,
  onSelectHypothesis,
}) => {
  const getLikelihoodBadge = (likelihood: HypothesisLikelihood) => {
    switch (likelihood) {
      case "LIKELY":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium tracking-wider bg-[#162722] text-verdigris border border-[#234A3E]">
            LIKELY
          </span>
        )
      case "POSSIBLE":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium tracking-wider bg-[#1B232D] text-slate border border-[#27384C]">
            POSSIBLE
          </span>
        )
      case "LESS_LIKELY":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium tracking-wider bg-[#241B1C] text-dust border border-ash/80">
            LESS LIKELY
          </span>
        )
    }
  }

  const getProgressBarColor = (likelihood: HypothesisLikelihood) => {
    switch (likelihood) {
      case "LIKELY":
        return "bg-verdigris"
      case "POSSIBLE":
        return "bg-slate"
      case "LESS_LIKELY":
        return "bg-dust/50"
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-1.5">
        <h4 className="text-xs font-semibold text-bone uppercase tracking-wider font-mono">
          Top Hypotheses
        </h4>
        <span className="text-[11px] text-dust font-mono">
          Deterministic scoring (evidence-weighted)
        </span>
      </div>

      <div className="space-y-2.5">
        {hypotheses.map((hyp) => {
          const isSelected = selectedHypothesisId === hyp.id

          return (
            <div
              key={hyp.id}
              onClick={() => onSelectHypothesis?.(hyp.id)}
              className={`p-3.5 rounded-md bg-ink/40 border transition-all cursor-pointer ${
                isSelected
                  ? "border-amber/80 bg-soot/80 shadow-sm"
                  : "border-ash/70 hover:border-ash hover:bg-ink/60"
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                {/* Left: Rank & Title */}
                <div className="flex items-start gap-2.5 min-w-0 flex-1">
                  <div className="w-5 h-5 rounded-full bg-soot border border-ash flex items-center justify-center font-mono text-xs font-semibold text-dust shrink-0 mt-0.5">
                    {hyp.rank}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-semibold text-bone leading-tight">{hyp.title}</div>
                    <div className="text-[11px] text-dust mt-0.5 leading-snug">
                      {hyp.description}
                    </div>
                  </div>
                </div>

                {/* Right: Progress Bar & Likelihood Badge matching reference image */}
                <div className="flex items-center gap-2.5 shrink-0 pt-0.5 self-end sm:self-auto">
                  {/* Progress Bar & Percentage */}
                  <div className="flex items-center gap-2">
                    <div className="w-16 sm:w-20 h-1.5 bg-[#25201B] rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ${getProgressBarColor(
                          hyp.likelihood
                        )}`}
                        style={{ width: `${hyp.score}%` }}
                      />
                    </div>
                    <span className="font-mono text-xs text-bone font-medium w-7 text-right">
                      {hyp.score}%
                    </span>
                  </div>

                  {/* Likelihood Tag */}
                  <div>{getLikelihoodBadge(hyp.likelihood)}</div>
                </div>
              </div>

              {/* Verification Callout if verified */}
              {hyp.verified && hyp.verificationReason && (
                <div className="mt-2.5 pt-2 border-t border-ash/50 flex items-start gap-2 text-[11px] text-verdigris font-mono">
                  <span className="w-1.5 h-1.5 rounded-full bg-verdigris shrink-0 mt-1" />
                  <span className="break-words [word-break:break-word] leading-normal flex-1">
                    {hyp.verificationReason}
                  </span>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
