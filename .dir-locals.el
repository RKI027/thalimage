;;; Directory Local Variables.   -*- no-byte-compile: t -*-
;;; Load the project's Emacs dev helpers (thalimage-dev.el) once per session
;;; and enable `thalimage-dev-mode' so the compile key restarts the dev stack.
;;; `compile-command' is the build, used by M-x compile invoked by name.
;;; Emacs will ask to confirm the eval the first time; answer "!" to mark it
;;; permanently safe for this project.

((nil . ((compile-command . "make fe-build")
         (eval . (progn
                   (unless (featurep 'thalimage-dev)
                     (when-let* ((root (locate-dominating-file
                                        default-directory "thalimage-dev.el")))
                       (load (expand-file-name "thalimage-dev.el" root)
                             :noerror :nomessage)))
                   (when (fboundp 'thalimage-dev-mode)
                     (thalimage-dev-mode 1)))))))
