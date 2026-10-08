import React from "react"
import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts"
import { FileCheck2, ArrowUpRight, ArrowDownRight, ArrowRight } from "lucide-react"
import { Card, CardHeader, CardTitle } from "../common/Card"
import { mockEvaluationSummary } from "../../mocks/evaluations"

interface EvaluationSummaryCardProps {
  onViewAll?: () => void
}

export const EvaluationSummaryCard: React.FC<EvaluationSummaryCardProps> = ({ onViewAll }) => {
  const {
    accuracyTop1,
    accuracyChange,
    avgSteps,
    stepsChange,
    avgTimeSeconds,
    timeChange,
    history,
  } = mockEvaluationSummary

  return (
    <Card className="flex flex-col h-full">
      <CardHeader>
        <CardTitle>
          <FileCheck2 className="w-4 h-4 text-verdigris" />
          <span>Evaluation Results</span>
        </CardTitle>
        {onViewAll && (
          <button
            onClick={onViewAll}
            className="text-xs text-dust hover:text-bone font-medium flex items-center gap-1 transition-colors group"
          >
            <span>View all</span>
            <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
          </button>
        )}
      </CardHeader>

      {/* KPI Stats Row matching reference */}
      <div className="grid grid-cols-3 gap-2 py-2 border-b border-ash/60">
        {/* Accuracy */}
        <div>
          <div className="text-base sm:text-lg font-semibold text-bone font-mono">
            {accuracyTop1}%
          </div>
          <div className="text-[10px] text-dust uppercase font-sans">Accuracy</div>
          <div className="text-[10px] text-verdigris flex items-center gap-0.5 font-mono mt-0.5">
            <ArrowUpRight className="w-3 h-3" />
            <span>{accuracyChange}%</span>
          </div>
        </div>

        {/* Avg Steps */}
        <div>
          <div className="text-base sm:text-lg font-semibold text-bone font-mono">{avgSteps}</div>
          <div className="text-[10px] text-dust uppercase font-sans">Avg Steps</div>
          <div className="text-[10px] text-verdigris flex items-center gap-0.5 font-mono mt-0.5">
            <ArrowDownRight className="w-3 h-3" />
            <span>{Math.abs(stepsChange)}%</span>
          </div>
        </div>

        {/* Avg Time */}
        <div>
          <div className="text-base sm:text-lg font-semibold text-bone font-mono">
            {avgTimeSeconds}s
          </div>
          <div className="text-[10px] text-dust uppercase font-sans">Avg Time</div>
          <div className="text-[10px] text-verdigris flex items-center gap-0.5 font-mono mt-0.5">
            <ArrowDownRight className="w-3 h-3" />
            <span>{Math.abs(timeChange)}%</span>
          </div>
        </div>
      </div>

      {/* Trend Area Chart matching reference */}
      <div className="h-32 w-full pt-3">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={history} margin={{ top: 5, right: 10, left: -25, bottom: 0 }}>
            <defs>
              <linearGradient id="evalGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#4FA38B" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#4FA38B" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="date"
              stroke="#5C564B"
              fontSize={10}
              tickLine={false}
              axisLine={{ stroke: "#332D26" }}
              fontFamily="monospace"
            />
            <YAxis
              domain={[0, 100]}
              ticks={[0, 50, 100]}
              stroke="#5C564B"
              fontSize={10}
              tickLine={false}
              axisLine={{ stroke: "#332D26" }}
              tickFormatter={(v) => `${v}%`}
              fontFamily="monospace"
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const dataPoint = payload[0].payload
                  return (
                    <div className="bg-soot border border-ash rounded p-2 text-xs font-mono shadow-lg">
                      <div className="text-dust">{dataPoint.date}</div>
                      <div className="text-verdigris font-medium">
                        Accuracy: {dataPoint.accuracy}%
                      </div>
                      <div className="text-bone text-[10px]">
                        Passed: {dataPoint.benchmarkPassCount}/20 faults
                      </div>
                    </div>
                  )
                }
                return null
              }}
            />
            <Area
              type="monotone"
              dataKey="accuracy"
              stroke="#4FA38B"
              strokeWidth={2}
              fill="url(#evalGradient)"
              dot={{ r: 2.5, fill: "#4FA38B" }}
              activeDot={{ r: 4, stroke: "#14110F", strokeWidth: 2 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}
