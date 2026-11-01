"use client";

import { cn } from "@advs/ui";
import { AlertTriangle, Info, XCircle } from "lucide-react";
import { useId } from "react";

export function Banner({
  tone,
  title,
  children,
  role,
}: {
  tone: "info" | "warning" | "danger";
  title?: string;
  children?: React.ReactNode;
  role?: "alert" | "status";
}) {
  const style = {
    info: "border-sky-200 bg-sky-50 text-sky-950",
    warning: "border-amber-200 bg-amber-50 text-amber-950",
    danger: "border-red-200 bg-red-50 text-red-950",
  }[tone];
  const Icon =
    tone === "info" ? Info : tone === "warning" ? AlertTriangle : XCircle;
  return (
    <div
      className={cn("flex gap-2.5 rounded-lg border p-3 text-sm", style)}
      role={role}
    >
      <Icon aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="min-w-0 space-y-1">
        {title ? <p className="font-semibold">{title}</p> : null}
        {children}
      </div>
    </div>
  );
}

const control =
  "h-9 rounded-md border border-border bg-white px-2.5 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:bg-muted disabled:text-muted-foreground";

export function SelectField({
  label,
  value,
  onChange,
  options,
  className,
  hideLabel,
  invalid,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  className?: string;
  hideLabel?: boolean;
  invalid?: boolean;
  placeholder?: string;
}) {
  const id = useId();
  return (
    <div className={cn("flex min-w-0 flex-col gap-1", className)}>
      <label
        className={cn(
          "text-xs font-medium text-muted-foreground",
          hideLabel && "sr-only",
        )}
        htmlFor={id}
      >
        {label}
      </label>
      <select
        aria-invalid={invalid || undefined}
        className={cn(control, invalid && "border-red-500")}
        id={id}
        onChange={(event) => onChange(event.target.value)}
        value={value}
      >
        {placeholder ? <option value="">{placeholder}</option> : null}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export function TextField({
  label,
  value,
  onChange,
  type = "text",
  inputMode,
  className,
  suffix,
  invalid,
  hideLabel,
  placeholder,
  min,
  max,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: "text" | "number" | "date";
  inputMode?: "numeric" | "decimal";
  className?: string;
  suffix?: string;
  invalid?: boolean;
  hideLabel?: boolean;
  placeholder?: string;
  min?: number;
  max?: number;
}) {
  const id = useId();
  return (
    <div className={cn("flex min-w-0 flex-col gap-1", className)}>
      <label
        className={cn(
          "text-xs font-medium text-muted-foreground",
          hideLabel && "sr-only",
        )}
        htmlFor={id}
      >
        {label}
      </label>
      <div className="flex items-center gap-1.5">
        <input
          aria-invalid={invalid || undefined}
          className={cn(control, "w-full", invalid && "border-red-500")}
          id={id}
          inputMode={inputMode}
          max={max}
          min={min}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          type={type}
          value={value}
        />
        {suffix ? (
          <span className="shrink-0 text-sm text-muted-foreground">
            {suffix}
          </span>
        ) : null}
      </div>
    </div>
  );
}

export function CheckField({
  label,
  checked,
  onChange,
  disabled,
  hint,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  hint?: string;
}) {
  const id = useId();
  return (
    <div className="flex items-start gap-2">
      <input
        checked={checked}
        className="mt-1 h-4 w-4 rounded border-border accent-[hsl(var(--primary))]"
        disabled={disabled}
        id={id}
        onChange={(event) => onChange(event.target.checked)}
        type="checkbox"
      />
      <label className="text-sm" htmlFor={id}>
        {label}
        {hint ? (
          <span className="block text-xs text-muted-foreground">{hint}</span>
        ) : null}
      </label>
    </div>
  );
}

export function RadioGroup({
  legend,
  name,
  value,
  onChange,
  options,
  inline,
}: {
  legend: string;
  name: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  inline?: boolean;
}) {
  return (
    <fieldset className="min-w-0">
      <legend className="mb-1 text-xs font-medium text-muted-foreground">
        {legend}
      </legend>
      <div
        className={cn("flex gap-3", inline ? "flex-row flex-wrap" : "flex-col")}
      >
        {options.map((option) => (
          <label
            className="flex items-center gap-1.5 text-sm"
            key={option.value}
          >
            <input
              checked={value === option.value}
              className="h-4 w-4 accent-[hsl(var(--primary))]"
              name={name}
              onChange={() => onChange(option.value)}
              type="radio"
              value={option.value}
            />
            {option.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function Sentence({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <p className="rounded-md border border-dashed border-border bg-muted/40 px-3 py-2 text-sm leading-relaxed">
      <span className="mr-1.5 text-xs font-semibold text-muted-foreground">
        {label}
      </span>
      {children}
    </p>
  );
}

export function FieldProblems({ problems }: { problems: string[] }) {
  if (!problems.length) return null;
  return (
    <div role="alert">
      <ul className="space-y-0.5 text-xs font-medium text-red-700">
        {problems.map((message) => (
          <li key={message}>{message}</li>
        ))}
      </ul>
    </div>
  );
}
