"use client";

import { useEffect, useRef } from "react";

/** A native modal dialog: focus is trapped and Escape closes it without extra code. */
export function Modal({
  title,
  onClose,
  children,
  wide,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (dialog && !dialog.open) dialog.showModal();
    return () => dialog?.close();
  }, []);
  return (
    <dialog
      aria-labelledby="modal-title"
      className={`max-h-[90vh] w-[calc(100%-2rem)] overflow-y-auto rounded-lg border border-border bg-white p-0 shadow-xl backdrop:bg-black/40 ${wide ? "max-w-4xl" : "max-w-xl"}`}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      ref={ref}
    >
      <div className="space-y-4 p-6">
        <h2 className="text-lg font-semibold" id="modal-title">
          {title}
        </h2>
        {children}
      </div>
    </dialog>
  );
}
