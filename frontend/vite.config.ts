import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

const apiProxy = {
	'/api': {
		target: 'http://127.0.0.1:8000',
		changeOrigin: true
	}
};

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		proxy: apiProxy
	},
	preview: {
		host: '127.0.0.1',
		port: 4173,
		allowedHosts: ['.ts.net'],
		proxy: apiProxy
	}
});
