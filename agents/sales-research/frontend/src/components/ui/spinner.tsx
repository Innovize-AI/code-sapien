import { cn } from "@/lib/utils"

interface SpinnerProps {
  size?: "xs" | "sm" | "md" | "lg"
  className?: string
}

const sizes = {
  xs: "h-2.5 w-2.5 border",
  sm: "h-3 w-3 border",
  md: "h-4 w-4 border-2",
  lg: "h-7 w-7 border-2",
}

export function Spinner({ size = "md", className }: SpinnerProps) {
  return (
    <div
      className={cn(
        "rounded-full animate-spin",
        "border-zinc-200 dark:border-zinc-700 border-t-primary",
        sizes[size],
        className,
      )}
    />
  )
}
