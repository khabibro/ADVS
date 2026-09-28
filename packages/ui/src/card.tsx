import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "./utils";

const cardVariants = cva("rounded-lg border bg-white", {
  variants: {
    tone: {
      plain: "border-border shadow-sm",
      muted: "border-border bg-muted/40",
      outline: "border-dashed border-border bg-white",
      success: "border-emerald-200 bg-emerald-50",
      warning: "border-amber-200 bg-amber-50",
      danger: "border-red-200 bg-red-50",
      info: "border-sky-200 bg-sky-50",
    },
    padding: {
      none: "p-0",
      sm: "p-3.5",
      md: "p-5",
      lg: "p-6",
    },
  },
  defaultVariants: { tone: "plain", padding: "md" },
});

export interface CardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {}

export function Card({ className, tone, padding, ...props }: CardProps) {
  return (
    <div className={cn(cardVariants({ tone, padding }), className)} {...props} />
  );
}

export { cardVariants };
