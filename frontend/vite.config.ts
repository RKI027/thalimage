import { execSync } from 'node:child_process';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

/**
 * The commit this bundle was built from, stamped in so a stale build can be
 * spotted by comparing it with the commit the backend reports.
 */
function buildCommit(): string | null {
	if (process.env.THALIMAGE_COMMIT) return process.env.THALIMAGE_COMMIT;
	try {
		return execSync('git describe --tags --always --dirty', { encoding: 'utf8' }).trim() || null;
	} catch {
		return null;
	}
}

const apiProxy = {
	'/api': {
		target: 'http://127.0.0.1:8000',
		changeOrigin: true
	}
};

export default defineConfig({
	plugins: [sveltekit()],
	define: {
		__BUILD_COMMIT__: JSON.stringify(buildCommit())
	},
	server: {
		proxy: apiProxy
	},
	preview: {
		host: '127.0.0.1',
		port: 4173,
		allowedHosts: ['.ts.net'],
		proxy: apiProxy
	},
	test: {
		environment: 'jsdom',
		include: ['src/**/*.test.ts'],
		// Stores read localStorage at import time; give each file a clean one.
		restoreMocks: true
	}
});
