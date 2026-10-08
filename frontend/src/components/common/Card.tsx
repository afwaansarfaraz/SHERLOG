import React from "react"
import { cn } from "../../lib/utils"

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  interactive?: boolean
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, interactive = false, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "bg-soot border border-ash rounded-lg p-4 sm:p-5 transition-colors",
          interactive && "hover:border-[#473E35] cursor-pointer",
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)
Card.displayName = "Card"

export const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "flex items-center justify-between gap-2 pb-3 mb-3 border-b border-ash/60",
        className
      )}
      {...props}
    />
  )
)
CardHeader.displayName = "CardHeader"

export const CardTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      "text-sm font-medium text-bone tracking-tight flex items-center gap-2",
      className
    )}
    {...props}
  />
))
CardTitle.displayName = "CardTitle"
