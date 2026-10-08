import React from "react"
import {
  ArrowLeft,
  AlertTriangle,
  Share2,
  FilePlus2,
  Play,
  Pause,
  RotateCcw,
  FastForward,
} from "lucide-react"
import { Badge } from "../common/Badge"
import { Button } from "../common/Button"

interface InvestigationHeaderProps {
  incidentId: string
  title: string
  service: string
  subtitle: string
  openedAt: string
  status: "INVESTIGATING" | "VERIFYING" | "RESOLVED"
  isPlaying: boolean
  currentStep: number
  totalSteps: number
  onBack: () => void
  onTogglePlay: () => void
  onReset: () => void
  onComplete: () => void
}

export const InvestigationHeader: React.FC<InvestigationHeaderProps> = ({
  incidentId,
  title,
  service,
  subtitle,
  openedAt,
  status,
  isPlaying,
  currentStep,
  totalSteps,
  onBack,
  onTogglePlay,
  onReset,
  onComplete,
}) => {
  return (
    <div className="space-y-3 pb-4 border-b border-ash">
      {/* Top Breadcrumb & Actions Bar matching reference */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Left: Back Link & Meta Badge */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 text-xs text-dust hover:text-bone font-mono transition-colors group cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
            <span className="font-semibold text-bone">{incidentId}</span>
          </button>

          <Badge variant={status === "INVESTIGATING" ? "investigating" : "resolved"}>
            {status}
          </Badge>

          <span className="text-xs text-dust font-mono hidden sm:inline-block">
            Opened {openedAt}
          </span>
        </div>

        {/* Right: Simulation Controls & Workspace Actions */}
        <div className="flex items-center gap-2">
          {/* Agent Loop Simulation Controls */}
          <div className="flex items-center gap-1 bg-soot border border-ash rounded p-0.5">
            <Button
              variant="ghost"
              size="sm"
              onClick={onTogglePlay}
              title={isPlaying ? "Pause simulation" : "Play agent investigation simulation"}
              className="h-6 px-2 text-[11px] font-mono text-dust hover:text-bone"
            >
              {isPlaying ? (
                <>
                  <Pause className="w-3 h-3 text-amber mr-1" />
                  <span>Pause</span>
                </>
              ) : (
                <>
                  <Play className="w-3 h-3 text-verdigris mr-1" />
                  <span>
                    Replay ({currentStep}/{totalSteps})
                  </span>
                </>
              )}
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={onReset}
              title="Reset simulation to Alert step"
              className="h-6 w-6 p-0 text-dust hover:text-bone"
            >
              <RotateCcw className="w-3 h-3" />
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={onComplete}
              title="Fast-forward to verified conclusion"
              className="h-6 w-6 p-0 text-dust hover:text-bone"
            >
              <FastForward className="w-3 h-3" />
            </Button>
          </div>

          <Button variant="outline" size="sm" className="hidden sm:inline-flex">
            <Share2 className="w-3.5 h-3.5 mr-1" />
            <span>Share</span>
          </Button>

          <Button variant="outline" size="sm" className="hidden sm:inline-flex">
            <FilePlus2 className="w-3.5 h-3.5 mr-1" />
            <span>Add Note</span>
          </Button>
        </div>
      </div>

      {/* Incident Title & Meta */}
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded bg-[#291714] border border-[#4A241E] flex items-center justify-center text-vermilion shrink-0 mt-0.5">
          <AlertTriangle className="w-4 h-4" />
        </div>
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-bone tracking-tight">{title}</h1>
          <p className="text-xs sm:text-sm text-dust mt-0.5">
            <span className="text-bone/90">{service}</span> • {subtitle}
          </p>
        </div>
      </div>
    </div>
  )
}
