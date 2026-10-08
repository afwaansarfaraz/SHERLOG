import type { EvaluationSummary } from "../types"

export const mockEvaluationSummary: EvaluationSummary = {
  accuracyTop1: 87.3,
  accuracyChange: 6.2,
  avgSteps: 2.4,
  stepsChange: -12.0,
  avgTimeSeconds: 18.6,
  timeChange: -28.0,
  history: [
    { date: "Aug 20", accuracy: 72.5, benchmarkPassCount: 14 },
    { date: "Aug 21", accuracy: 74.0, benchmarkPassCount: 15 },
    { date: "Aug 22", accuracy: 78.2, benchmarkPassCount: 16 },
    { date: "Aug 23", accuracy: 81.5, benchmarkPassCount: 17 },
    { date: "Aug 24", accuracy: 83.0, benchmarkPassCount: 17 },
    { date: "Aug 25", accuracy: 85.1, benchmarkPassCount: 18 },
    { date: "Aug 26", accuracy: 87.3, benchmarkPassCount: 19 },
  ],
}
