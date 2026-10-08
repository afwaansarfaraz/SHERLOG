export interface BenchmarkHistoryPoint {
  date: string
  accuracy: number
  benchmarkPassCount: number
}

export interface EvaluationSummary {
  accuracyTop1: number
  accuracyChange: number
  avgSteps: number
  stepsChange: number
  avgTimeSeconds: number
  timeChange: number
  history: BenchmarkHistoryPoint[]
}
