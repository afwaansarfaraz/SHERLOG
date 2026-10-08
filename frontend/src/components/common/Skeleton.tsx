import React from "react"
import { cn } from "../../lib/utils"

export const Skeleton: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  ...props
}) => {
  return <div className={cn("animate-pulse bg-[#25201B] rounded", className)} {...props} />
}
