import React from "react"
import { CheckCircle2, Clock, CircleDot, Circle } from "lucide-react"
import { Card, CardHeader, CardTitle } from "../common/Card"
import type { InvestigationStep } from "../../types"

interface InvestigationProgressProps {
  steps: InvestigationStep[]
  currentStepIndex: number
}

export const InvestigationProgress: React.FC<InvestigationProgressProps> = ({
  steps,
  currentStepIndex,
}) => {
  return (
    <Card className="flex flex-col h-full">
      <CardHeader>
        <CardTitle>
          <Clock className="w-4 h-4 text-dust" />
          <span>Investigation Progress</span>
        </CardTitle>
      </CardHeader>

      <div className="space-y-4 flex-1 py-1 relative">
        {steps.map((step, idx) => {
          const isCompleted = idx < currentStepIndex
          const isActive = idx === currentStepIndex - 1 && currentStepIndex < steps.length
          const isLast = idx === steps.length - 1

          return (
            <div key={step.id} className="relative flex items-start gap-3 group">
              {/* Vertical connecting line */}
              {!isLast && (
                <div
                  className={`absolute left-[11px] top-6 bottom-[-16px] w-px ${
                    isCompleted ? "bg-verdigris/40" : "bg-ash/70"
                  }`}
                />
              )}

              {/* Step Node Icon */}
              <div className="shrink-0 relative z-10">
                {isCompleted ? (
                  <div className="w-6 h-6 rounded-full bg-[#162722] border border-[#234A3E] flex items-center justify-center text-verdigris">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                  </div>
                ) : isActive ? (
                  <div className="w-6 h-6 rounded-full bg-[#291714] border border-[#4A241E] flex items-center justify-center text-vermilion">
                    <CircleDot className="w-3.5 h-3.5 animate-pulse" />
                  </div>
                ) : (
                  <div className="w-6 h-6 rounded-full bg-soot border border-ash/80 flex items-center justify-center text-dust">
                    <Circle className="w-3 h-3 text-dust/60" />
                  </div>
                )}
              </div>

              {/* Step Title & Timestamp matching reference image */}
              <div className="min-w-0 flex-1 pt-0.5">
                <div
                  className={`text-xs font-medium tracking-tight ${
                    isCompleted ? "text-bone" : isActive ? "text-vermilion" : "text-dust"
                  }`}
                >
                  {step.title}
                </div>

                <div className="text-[11px] font-mono text-dust/80 mt-0.5">
                  {isCompleted && step.timestamp ? (
                    step.timestamp
                  ) : isActive ? (
                    <span className="text-amber">In progress...</span>
                  ) : (
                    "Pending"
                  )}
                </div>

                {/* Subtitle / Details if active or recently completed */}
                {step.details && (isCompleted || isActive) && (
                  <div className="text-[11px] text-dust/70 mt-1 leading-snug line-clamp-2">
                    {step.details}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
