import { ButtonHTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

type ButtonVariant = "default" | "outline" | "ghost";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
};

const variantStyles: Record<ButtonVariant, string> = {
  default:
    "border border-primary/70 bg-primary/90 text-[#07111f] hover:bg-primary focus-visible:ring-primary/50",
  outline:
    "border border-white/20 bg-white/[0.04] text-fg hover:bg-white/[0.08] focus-visible:ring-white/20",
  ghost:
    "border border-transparent bg-transparent text-fg-muted hover:border-white/15 hover:bg-white/[0.05] hover:text-fg focus-visible:ring-white/20",
};

export function Button({ className, variant = "default", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2",
        variantStyles[variant],
        className,
      )}
      {...props}
    />
  );
}
