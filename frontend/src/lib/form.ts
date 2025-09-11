import type { SubmitFunction } from '@sveltejs/kit';

export const enhance = (() => {
	return (form: HTMLFormElement, {
		pending,
		error,
		result
	}) => {
		let F: SubmitFunction = async ({ update }) => {
			pending && pending();

			try {
				await update();
			} catch (e) {
				error && error({ error: e });
				return;
			}

			result && result();
		};

		return F;
	};
})();