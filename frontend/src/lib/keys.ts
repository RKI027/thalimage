// Inputs that take no typing: keyboard shortcuts stay live while they
// have focus, as after dragging a slider.
const NOT_TYPED = new Set(['range', 'checkbox', 'radio', 'button', 'submit', 'reset', 'color', 'file']);

/** Whether keys pressed on `target` type into it, so shortcuts should
 * leave them alone. */
export function isTextEntry(target: EventTarget | null): boolean {
	if (!(target instanceof Element)) return false;
	if (target.closest('textarea, select, [contenteditable="true"], [contenteditable=""]')) return true;
	return target instanceof HTMLInputElement && !NOT_TYPED.has(target.type);
}
