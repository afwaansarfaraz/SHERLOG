import React from "react"
import { cn } from "../../lib/utils"

export type ButtonVariant = "default" | "secondary" | "outline" | "ghost" | "verdigris" | "oxblood"
export type ButtonSize = "sm" | "md" | "lg" | "icon"

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  isLoading?: boolean
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "secondary",
      size = "md",
      isLoading = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const variants: Record<ButtonVariant, string> = {
      default:
        "bg-bone text-ink hover:bg-[#D4CDBC] active:bg-[#C2BAA6] border border-transparent font-medium",
      secondary:
        "bg-soot text-bone border border-ash hover:border-[#4A4237] hover:bg-[#25201B] active:bg-[#1D1915]",
      outline:
        "bg-transparent text-dust border border-ash hover:text-bone hover:border-[#4A4237] active:bg-soot",
      ghost:
        "bg-transparent text-dust hover:text-bone hover:bg-soot/80 active:bg-soot border border-transparent",
      verdigris:
        "bg-verdigris text-ink font-semibold hover:bg-[#43917A] active:bg-[#3A806C] border border-transparent",
      oxblood:
        "bg-[#291417] text-[#D96B78] border border-[#522127] hover:bg-[#36191E] active:bg-[#241113]",
    }

    const sizes: Record<ButtonSize, string> = {
      sm: "h-7 px-2.5 text-xs rounded",
      md: "h-8 px-3 text-xs rounded-md",
      lg: "h-9 px-4 text-sm rounded-md",
      icon: "h-8 w-8 p-0 rounded-md flex items-center justify-center",
    }

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(
          "inline-flex items-center justify-center gap-1.5 font-sans transition-all select-none disabled:opacity-50 disabled:pointer-events-none cursor-pointer outline-none focus-visible:ring-1 focus-visible:ring-ash",
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      >
        {isLoading ? (
          <span className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
        ) : null}
        {children}
      </button>
    )
  }
)
Button.displayName = "Button"
