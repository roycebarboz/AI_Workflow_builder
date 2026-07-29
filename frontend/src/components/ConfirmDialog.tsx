import "./ConfirmDialog.css";

interface ConfirmDialogProps {
  title: string;
  desc: string;
  confirmLabel: string;
  isBusy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  title,
  desc,
  confirmLabel,
  isBusy,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <div className="confirm-overlay" onClick={onCancel}>
      <div className="confirm-box" role="alertdialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <div className="confirm-title">{title}</div>
        <p className="confirm-desc">{desc}</p>
        <div className="confirm-actions">
          <button type="button" className="btn-secondary" onClick={onCancel} disabled={isBusy}>
            Cancel
          </button>
          <button type="button" className="btn-danger" onClick={onConfirm} disabled={isBusy}>
            {isBusy ? "Deleting…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
