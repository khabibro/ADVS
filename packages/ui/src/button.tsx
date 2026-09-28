import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "./utils";

/**
 * The single button definition for the product. Variants exist so no screen
 * has to hand-roll button styling with ad-hoc Tailwind values.
 */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md font-medium transition disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2",
  {
    variants: {
      variant: {
        primary:
          "bg-primary text-primary-foreground shadow-sm hover:bg-primary/90",
        secondary:
          "border border-border bg-white text-foreground hover:bg-muted",
        ghost: "text-foreground hover:bg-muted",
        danger:
          "border border-red-300 bg-white text-red-800 hover:bg-red-50",
      },
      size: {
        md: "h-10 px-4 text-sm",
        sm: "h-9 px-3 text-sm",
        xs: "h-8 px-2.5 text-xs",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export function Button({
  className,
  variant,
  size,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(buttonVariants({ variant, size }), className)}
      type={type}
      {...props}
    />
  );
}

export { buttonVariants };
