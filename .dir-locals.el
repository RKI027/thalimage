;;; Directory Local Variables.   -*- no-byte-compile: t -*-
;;; Load the project's Emacs dev helpers (thalimage-dev.el) once per session so
;;; M-x thalimage-dev-start / -restart etc. are available when resuming work.
;;; Emacs will ask to confirm this eval the first time; answer "!" to mark it
;;; permanently safe for this project.

((nil . ((eval . (unless (featurep 'thalimage-dev)
                   (when-let* ((root (locate-dominating-file
                                      default-directory "thalimage-dev.el")))
                     (load (expand-file-name "thalimage-dev.el" root)
                           :noerror :nomessage)))))))
