;;; thalimage-dev.el --- Dev process helpers for Thalimage -*- lexical-binding: t; -*-

;; Author: Thalimage contributors
;; Keywords: tools, processes

;;; Commentary:

;; Interactive commands to run the Thalimage dev stack from Emacs without
;; manually juggling terminal buffers.  Each process runs in its own
;; `compilation-mode' buffer and is restarted in place when re-invoked.
;;
;; Commands:
;;   `thalimage-dev-start'    backend + frontend dev servers
;;   `thalimage-dev-restart'  stop then start both (the "restart everything" verb)
;;   `thalimage-dev-stop'     stop both
;;   `thalimage-dev-backend'  backend only ("make dev")
;;   `thalimage-dev-frontend' frontend only ("make fe-dev")
;;   `thalimage-dev-build'    build the frontend bundle ("make fe-build")
;;
;; The accompanying .dir-locals.el loads this file on first visit of a file
;; in the project, so the commands are available via M-x when you resume work.

;;; Code:

(require 'compile)

(defvar thalimage-dev-root
  (file-name-directory (or load-file-name buffer-file-name default-directory))
  "Absolute path to the Thalimage project root (where this file lives).")

(defun thalimage-dev--run (name command)
  "Run COMMAND from the project root in a buffer dedicated to NAME.
A previous process for NAME is terminated first, so the call restarts it.
Return the compilation buffer."
  (let ((bufname (format "*thalimage:%s*" name)))
    (when-let* ((existing (get-buffer bufname)))
      (let ((kill-buffer-query-functions nil))
        (kill-buffer existing)))
    (let ((default-directory thalimage-dev-root))
      (compilation-start command nil (lambda (&rest _) bufname)))))

(defun thalimage-dev-backend ()
  "Start (or restart) the backend dev server (\"make dev\")."
  (interactive)
  (thalimage-dev--run "backend" "make dev"))

(defun thalimage-dev-frontend ()
  "Start (or restart) the frontend dev server (\"make fe-dev\")."
  (interactive)
  (thalimage-dev--run "frontend" "make fe-dev"))

(defun thalimage-dev-build ()
  "Build the frontend bundle (\"make fe-build\")."
  (interactive)
  (thalimage-dev--run "build" "make fe-build"))

(defun thalimage-dev-start ()
  "Start the backend and frontend dev servers."
  (interactive)
  (thalimage-dev-backend)
  (thalimage-dev-frontend))

(defun thalimage-dev-stop ()
  "Stop the backend and frontend dev servers."
  (interactive)
  (dolist (name '("backend" "frontend"))
    (when-let* ((buf (get-buffer (format "*thalimage:%s*" name))))
      (let ((kill-buffer-query-functions nil))
        (kill-buffer buf)))))

(defun thalimage-dev-restart ()
  "Restart the backend and frontend dev servers."
  (interactive)
  (thalimage-dev-stop)
  (thalimage-dev-start))

(defvar thalimage-dev-mode-map
  (let ((map (make-sparse-keymap)))
    (define-key map [remap compile] #'thalimage-dev-restart)
    (define-key map [remap recompile] #'thalimage-dev-restart)
    (define-key map [remap project-compile] #'thalimage-dev-restart)
    map)
  "Keymap for `thalimage-dev-mode'.
Remaps the compile commands to `thalimage-dev-restart' so the usual
\"compile\" keybinding restarts the dev stack.")

(define-minor-mode thalimage-dev-mode
  "Buffer-local mode that makes the compile commands restart the dev stack.
Enabled per project via .dir-locals.el; pressing the key bound to
`compile' (or `recompile' / `project-compile') runs `thalimage-dev-restart'."
  :lighter " ThaliDev"
  :keymap thalimage-dev-mode-map)

(provide 'thalimage-dev)

;;; thalimage-dev.el ends here
