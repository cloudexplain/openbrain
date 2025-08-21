<script lang="ts">
	import { onMount, createEventDispatcher } from "svelte";

	const dispatch = createEventDispatcher();

	interface Tag {
		id: string;
		name: string;
		description: string | null;
		color: string;
		document_count: number;
		created_at: string;
		updated_at: string;
	}

	let tags: Tag[] = [];
	let isLoading = false;
	let searchQuery = "";
	let selectedTag: Tag | null = null;
	let isEditing = false;
	let isCreating = false;

	// Form data
	let formData = {
		name: "",
		description: "",
		color: "#808080",
	};

	onMount(async () => {
		await loadTags();
	});

	async function loadTags() {
		isLoading = true;
		try {
			const response = await fetch("/api/v1/tags");
			if (!response.ok)
				throw new Error("Failed to load tags");

			const data = await response.json();
			tags = data.tags;
		} catch (error) {
			console.error("Failed to load tags:", error);
			dispatch("notification", {
				message: "Failed to load tags",
				type: "error",
			});
		} finally {
			isLoading = false;
		}
	}

	async function createTag() {
		try {
			// Validate and normalize color format
			if (!formData.color.match(/^#[0-9a-fA-F]{6}$/)) {
				dispatch("notification", {
					message: "Invalid color format. Please use hex format like #808080",
					type: "error",
				});
				return;
			}
			
			// Ensure color is lowercase for consistency
			const normalizedData = {
				...formData,
				color: formData.color.toLowerCase()
			};
			
			console.log("Creating tag with data:", normalizedData);
			const response = await fetch("/api/v1/tags", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(normalizedData),
			});

			if (!response.ok) {
				const error = await response.json();
				console.error(
					"Backend validation error:",
					error,
				);
				throw new Error(
					error.detail || "Failed to create tag",
				);
			}

			const newTag = await response.json();
			tags = [newTag, ...tags];
			resetForm();
			isCreating = false;

			dispatch("notification", {
				message: `Tag "${newTag.name}" created successfully`,
				type: "success",
			});
		} catch (error) {
			dispatch("notification", {
				message:
					error.message || "Failed to create tag",
				type: "error",
			});
		}
	}

	async function updateTag() {
		if (!selectedTag) return;

		try {
			// Validate and normalize color format
			if (!formData.color.match(/^#[0-9a-fA-F]{6}$/)) {
				dispatch("notification", {
					message: "Invalid color format. Please use hex format like #808080",
					type: "error",
				});
				return;
			}
			
			// Ensure color is lowercase for consistency
			const normalizedData = {
				...formData,
				color: formData.color.toLowerCase()
			};
			
			const response = await fetch(
				`/api/v1/tags/${selectedTag.id}`,
				{
					method: "PUT",
					headers: {
						"Content-Type":
							"application/json",
					},
					body: JSON.stringify(normalizedData),
				},
			);

			if (!response.ok) {
				const error = await response.json();
				throw new Error(
					error.detail || "Failed to update tag",
				);
			}

			const updatedTag = await response.json();
			tags = tags.map((t) =>
				t.id === updatedTag.id ? updatedTag : t,
			);
			resetForm();
			isEditing = false;
			selectedTag = null;

			dispatch("notification", {
				message: `Tag "${updatedTag.name}" updated successfully`,
				type: "success",
			});
		} catch (error) {
			dispatch("notification", {
				message:
					error.message || "Failed to update tag",
				type: "error",
			});
		}
	}

	async function deleteTag(tag: Tag) {
		if (
			!confirm(
				`Delete tag "${tag.name}"? This will remove it from all documents.`,
			)
		) {
			return;
		}

		try {
			const response = await fetch(`/api/v1/tags/${tag.id}`, {
				method: "DELETE",
			});

			if (!response.ok)
				throw new Error("Failed to delete tag");

			tags = tags.filter((t) => t.id !== tag.id);

			dispatch("notification", {
				message: `Tag "${tag.name}" deleted successfully`,
				type: "success",
			});
		} catch (error) {
			dispatch("notification", {
				message: "Failed to delete tag",
				type: "error",
			});
		}
	}

	function startEdit(tag: Tag) {
		selectedTag = tag;
		formData = {
			name: tag.name,
			description: tag.description || "",
			color: tag.color,
		};
		isEditing = true;
		isCreating = false;
	}

	function startCreate() {
		resetForm();
		isCreating = true;
		isEditing = false;
		selectedTag = null;
	}

	function resetForm() {
		formData = {
			name: "",
			description: "",
			color: "#808080",
		};
	}

	function cancelEdit() {
		resetForm();
		isEditing = false;
		isCreating = false;
		selectedTag = null;
	}

	// Handle color changes from the color picker
	function handleColorChange(e: Event) {
		const target = e.target as HTMLInputElement;
		formData.color = target.value.toLowerCase();
	}

	$: filteredTags = tags.filter(
		(tag) =>
			tag.name
				.toLowerCase()
				.includes(searchQuery.toLowerCase()) ||
			(tag.description &&
				tag.description
					.toLowerCase()
					.includes(searchQuery.toLowerCase())),
	);
</script>

<div class="flex flex-col h-full bg-gray-50">
	<!-- Header -->
	<div class="bg-white border-b border-gray-200 px-6 py-4">
		<div class="flex items-center justify-between">
			<h2 class="text-xl font-semibold text-gray-900">
				Tag Management
			</h2>
			<button
				on:click={() => dispatch("close")}
				class="p-2 hover:bg-gray-100 rounded-lg transition-colors"
			>
				<svg
					class="w-5 h-5"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M6 18L18 6M6 6l12 12"
					/>
				</svg>
			</button>
		</div>
	</div>

	<!-- Search and Actions -->
	<div class="bg-white border-b border-gray-200 px-6 py-3">
		<div class="flex gap-4">
			<div class="flex-1 relative">
				<input
					type="text"
					bind:value={searchQuery}
					placeholder="Search tags..."
					class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
				/>
				<svg
					class="absolute left-3 top-2.5 w-5 h-5 text-gray-400"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
					/>
				</svg>
			</div>
			<button
				on:click={startCreate}
				class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors flex items-center gap-2"
			>
				<svg
					class="w-5 h-5"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M12 4v16m8-8H4"
					/>
				</svg>
				New Tag
			</button>
		</div>
	</div>

	<!-- Content -->
	<div class="flex-1 flex overflow-hidden">
		<!-- Tag List -->
		<div class="w-1/2 border-r border-gray-200 overflow-y-auto">
			{#if isLoading}
				<div
					class="flex items-center justify-center h-32"
				>
					<div
						class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"
					></div>
				</div>
			{:else if filteredTags.length === 0}
				<div class="p-8 text-center text-gray-500">
					{searchQuery
						? "No tags found matching your search"
						: "No tags created yet"}
				</div>
			{:else}
				<div class="divide-y divide-gray-200">
					{#each filteredTags as tag}
						<div
							class="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
							class:bg-blue-50={selectedTag?.id ===
								tag.id}
							on:click={() =>
								startEdit(tag)}
						>
							<div
								class="flex items-center justify-between"
							>
								<div
									class="flex items-center gap-3"
								>
									<div
										class="w-8 h-8 rounded-full"
										style="background-color: {tag.color}"
									></div>
									<div>
										<div
											class="font-medium text-gray-900"
										>
											{tag.name}
										</div>
										{#if tag.description}
											<div
												class="text-sm text-gray-500 truncate max-w-xs"
											>
												{tag.description}
											</div>
										{/if}
									</div>
								</div>
								<div
									class="flex items-center gap-2"
								>
									<span
										class="text-sm text-gray-500"
									>
										{tag.document_count}
										{tag.document_count ===
										1
											? "document"
											: "documents"}
									</span>
									<button
										on:click|stopPropagation={() =>
											deleteTag(
												tag,
											)}
										class="p-1 hover:bg-red-100 rounded transition-colors"
									>
										<svg
											class="w-4 h-4 text-red-500"
											fill="none"
											stroke="currentColor"
											viewBox="0 0 24 24"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
											/>
										</svg>
									</button>
								</div>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Edit/Create Form -->
		<div class="w-1/2 p-6 overflow-y-auto">
			{#if isEditing || isCreating}
				<form
					on:submit|preventDefault={isCreating
						? createTag
						: updateTag}
				>
					<h3 class="text-lg font-semibold mb-4">
						{isCreating
							? "Create New Tag"
							: "Edit Tag"}
					</h3>

					<div class="space-y-4">
						<div>
							<label
								for="name"
								class="block text-sm font-medium text-gray-700 mb-1"
							>
								Name *
							</label>
							<input
								id="name"
								type="text"
								bind:value={
									formData.name
								}
								required
								maxlength="50"
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
							/>
						</div>

						<div>
							<label
								for="description"
								class="block text-sm font-medium text-gray-700 mb-1"
							>
								Description
							</label>
							<textarea
								id="description"
								bind:value={
									formData.description
								}
								rows="3"
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
							></textarea>
						</div>

						<div>
							<label
								for="color"
								class="block text-sm font-medium text-gray-700 mb-1"
							>
								Color
							</label>
							<div
								class="flex items-center gap-2"
							>
								<input
									id="color"
									type="color"
									value={formData.color}
									on:input={handleColorChange}
									class="h-10 w-20"
								/>
								<input
									type="text"
									bind:value={
										formData.color
									}
									maxlength="7"
									placeholder="#808080"
									class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
								/>
							</div>
						</div>

						<div class="flex gap-2 pt-4">
							<button
								type="submit"
								class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
							>
								{isCreating
									? "Create"
									: "Update"}
							</button>
							<button
								type="button"
								on:click={cancelEdit}
								class="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg transition-colors"
							>
								Cancel
							</button>
						</div>
					</div>
				</form>
			{:else}
				<div
					class="flex items-center justify-center h-full text-gray-500"
				>
					Select a tag to edit or create a new one
				</div>
			{/if}
		</div>
	</div>
</div>
