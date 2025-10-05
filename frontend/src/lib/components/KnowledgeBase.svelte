<script lang="ts">
  import { onMount, createEventDispatcher } from "svelte";
  import { marked } from "marked";
  import type {
    Document,
    DocumentDetail,
    DocumentWithChunks,
    DocumentChunk,
  } from "$lib/api";
  import { Folder, FolderOpen } from "@lucide/svelte";

  interface Folder {
    id: string;
    name: string;
    description?: string;
    color: string;
    parent_id?: string;
    children: Folder[];
    document_count: number;
    created_at: string;
    updated_at: string;
  }
  import PushNotification from "./PushNotification.svelte";
  import TagSelector from "./TagSelector.svelte";
  import TipTapEditor from "./TipTapEditor.svelte";
  import { invalidateAll } from "$app/navigation";

  const dispatch = createEventDispatcher();

  // Auto-resize textarea action
  function autoResize(node: HTMLTextAreaElement) {
    function resize() {
      node.style.height = "auto";
      // Set min height to 100px, but expand as needed
      const scrollHeight = node.scrollHeight;
      node.style.height = Math.max(100, scrollHeight) + "px";
    }

    // Initial resize
    resize();

    // Resize on input
    node.addEventListener("input", resize);

    return {
      destroy() {
        node.removeEventListener("input", resize);
      },
    };
  }

  export let documents: Document[] = [];
  // Use internal state for documents that can be updated
  let internalDocuments: Document[] = documents;
  export let highlightChunks: string[] = [];
  export let highlightPages: number[] = [];
  let selectedDocument: DocumentDetail | null = null;
  let selectedDocumentChunks: DocumentWithChunks | null = null;

  // Folder state
  let folders: Folder[] = [];
  let selectedFolder: Folder | null = null;
  let expandedFolders: Set<string> = new Set();
  let showCreateFolderModal = false;
  let newFolderName = "";
  let newFolderDescription = "";
  let newFolderColor = "#4F46E5";
  let newFolderParentId: string | null = null;

  // Document move state
  let showMoveDocumentModal = false;
  let documentToMove: Document | null = null;
  let targetFolderId: string | null = null;

  // Folder delete state
  let showDeleteFolderModal = false;
  let folderToDelete: Folder | null = null;

  // Chunk data for highlighting
  let chunkData: any[] = [];
  let highlightedContent = "";
  let isLoading = false;
  let searchQuery = "";
  let documentLoading = false;
  let parsedContent = "";
  let showUploadModal = false;
  let uploadLoading = false;
  let uploadedFiles: File[] = [];
  let isDragging = false;
  let uploadProgress: {
    [key: string]: { progress: number; status: string };
  } = {};
  let isEditMode = false;
  let editedChunks: DocumentChunk[] = [];
  let editedTitle = "";
  let editedContent = ""; // Single unified content for editing
  let hasChanges = false;
  let displayMode: "formatted" | "raw" = "formatted"; // Display mode toggle

  // Cache for loaded documents to avoid re-fetching
  let documentCache: Map<string, DocumentDetail> = new Map();
  let showDeleteModal = false;
  let documentToDelete: DocumentDetail | null = null;

  // PDF viewer state
  let viewMode: "raw" | "pdf" = "raw";
  let isPdfDocument = false;

  // Upload folder selection
  let selectedUploadFolder: string | null = null;

  // Drag and drop state
  let draggedDocument: Document | null = null;
  let dropTargetFolder: string | null = null;

  // Placeholder for uploading files
  let uploadingFiles: { name: string; id: number }[] = [];
  let nextUploadId = 0;

  // Reactive logic to remove placeholders when documents are loaded
  $: {
    if (uploadingFiles.length > 0 && documents.length > 0) {
      const documentTitles = new Set(documents.map((d) => d.title));
      const stillUploading = uploadingFiles.filter((file) => {
        // Check against original name and name without extension
        const baseName = file.name.includes(".")
          ? file.name.substring(0, file.name.lastIndexOf("."))
          : file.name;
        return !documentTitles.has(file.name) && !documentTitles.has(baseName);
      });

      if (stillUploading.length < uploadingFiles.length) {
        uploadingFiles = stillUploading;
      }
    }
  }

  // Push notifications
  let pushNotifications: Array<{
    id: number;
    message: string;
    type: "success" | "error" | "info" | "processing";
    duration: number;
  }> = [];
  let notificationId = 0;

  // Configure marked options
  marked.setOptions({
    breaks: true, // Enable line breaks
    gfm: true, // Enable GitHub Flavored Markdown
  });

  onMount(async () => {
    // Initialize internal documents from props
    internalDocuments = documents;
    sortDocuments();
    await loadFolders();
    // Load documents to get the latest data including folder_id
    await loadDocuments();
  });

  function sortDocuments() {
    // Sort by created_at descending
    internalDocuments = internalDocuments.sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }

  async function loadDocuments() {
    // Clear document cache when refreshing list
    documentCache.clear();
    // Refresh documents from server
    try {
      const response = await fetch("/api/v1/documents");
      if (response.ok) {
        const data = await response.json();
        internalDocuments = data.documents || data;
        console.log(
          "Reloaded documents:",
          internalDocuments.length,
          "documents"
        );
        console.log("Raw API response:", data);
        console.log("All documents with folder info:", internalDocuments);
      } else {
        console.error("Failed to reload documents:", response.status);
      }
    } catch (error) {
      console.error("Error reloading documents:", error);
    }
  }

  async function loadFolders() {
    try {
      const response = await fetch("/api/v1/folders/");
      if (response.ok) {
        folders = await response.json();
        console.log("Loaded folders:", folders);
      } else {
        const errorData = await response.text();
        console.error("Failed to load folders:", response.status, errorData);
      }
    } catch (error) {
      console.error("Error loading folders:", error);
    }
  }

  function toggleFolderExpansion(folderId: string) {
    if (expandedFolders.has(folderId)) {
      expandedFolders.delete(folderId);
    } else {
      expandedFolders.add(folderId);
    }
    expandedFolders = expandedFolders; // Trigger reactivity
  }

  function selectFolder(folder: Folder | null) {
    console.log("Selecting folder:", folder?.name, folder?.id);
    selectedFolder = folder;
    // Automatically expand the folder when selected
    if (folder) {
      expandedFolders.add(folder.id);
      expandedFolders = expandedFolders; // Trigger reactivity
    }
    // Clear selected document when selecting a folder
    selectedDocument = null;
  }

  async function createFolder() {
    if (!newFolderName.trim()) return;

    try {
      const response = await fetch("/api/v1/folders/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: newFolderName,
          description: newFolderDescription || null,
          color: newFolderColor,
          parent_id: newFolderParentId,
        }),
      });

      if (response.ok) {
        await loadFolders();
        showPushNotification(
          `Folder "${newFolderName}" created successfully`,
          "success"
        );
        resetCreateFolderModal();
      } else {
        const errorData = await response.text();
        console.error("Create folder error:", response.status, errorData);
        throw new Error(
          `Failed to create folder: ${response.status} - ${errorData}`
        );
      }
    } catch (error) {
      console.error("Failed to create folder:", error);
      showPushNotification("Failed to create folder", "error");
    }
  }

  function resetCreateFolderModal() {
    showCreateFolderModal = false;
    newFolderName = "";
    newFolderDescription = "";
    newFolderColor = "#4F46E5";
    newFolderParentId = null;
  }

  function showMoveDocument(doc: Document) {
    documentToMove = doc;
    targetFolderId = (doc as any).folder_id || null;
    showMoveDocumentModal = true;
  }

  function resetMoveDocumentModal() {
    showMoveDocumentModal = false;
    documentToMove = null;
    targetFolderId = null;
  }

  function showDeleteFolder(folder: Folder) {
    folderToDelete = folder;
    showDeleteFolderModal = true;
  }

  function resetDeleteFolderModal() {
    showDeleteFolderModal = false;
    folderToDelete = null;
  }

  async function deleteFolder() {
    if (!folderToDelete) return;

    const deletingNotificationId = showPushNotification(
      `Deleting folder "${folderToDelete.name}"...`,
      "processing",
      0
    );

    try {
      const response = await fetch(`/api/v1/folders/${folderToDelete.id}`, {
        method: "DELETE",
      });

      if (response.ok) {
        await loadFolders();
        await loadDocuments(); // Refresh documents as some may have moved
        showPushNotification(
          `Folder "${folderToDelete.name}" deleted successfully`,
          "success"
        );

        // Clear selected folder if it was the one being deleted
        if (selectedFolder?.id === folderToDelete.id) {
          selectFolder(null);
        }

        resetDeleteFolderModal();
        removePushNotification(deletingNotificationId);
      } else {
        const errorData = await response.text();
        console.error("Delete folder error:", response.status, errorData);
        throw new Error(
          `Failed to delete folder: ${response.status} - ${errorData}`
        );
      }
    } catch (error) {
      console.error("Failed to delete folder:", error);
      removePushNotification(deletingNotificationId);
      showPushNotification("Failed to delete folder", "error");
    }
  }

  async function moveDocument() {
    if (!documentToMove) return;

    console.log(
      "Moving document:",
      documentToMove.id,
      "to folder:",
      targetFolderId
    );

    try {
      const url = new URL(
        `/api/v1/documents/${documentToMove.id}/move`,
        window.location.origin
      );
      if (targetFolderId) {
        url.searchParams.set("folder_id", targetFolderId);
      }

      console.log("Move URL:", url.toString());

      const response = await fetch(url.toString(), {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (response.ok) {
        const result = await response.json();
        console.log("Move document result:", result);

        await loadDocuments();
        await loadFolders(); // Refresh folder document counts
        showPushNotification(
          `Document moved ${targetFolderId ? "to folder" : "to root"}`,
          "success"
        );
        resetMoveDocumentModal();
      } else {
        const errorData = await response.text();
        console.error("Move document error:", response.status, errorData);
        throw new Error(
          `Failed to move document: ${response.status} - ${errorData}`
        );
      }
    } catch (error) {
      console.error("Failed to move document:", error);
      showPushNotification("Failed to move document", "error");
    }
  }

  async function selectDocument(doc: Document) {
    // Reset PDF state
    isPdfDocument = false;

    // Check cache first
    if (documentCache.has(doc.id)) {
      selectedDocument = documentCache.get(doc.id) || null;
      if (selectedDocument) {
        parsedContent = marked.parse(selectedDocument.content) as string;
        // Check if it's a PDF document and set view mode accordingly
        isPdfDocument = selectedDocument.file_type === "application/pdf";
        viewMode = isPdfDocument ? "pdf" : "raw";

        // Load chunk data for highlighting if needed
        await loadChunkDataForHighlighting();
      }
      return;
    }

    documentLoading = true;
    try {
      const response = await fetch(`/api/v1/documents/${doc.id}`);

      if (!response.ok) {
        throw new Error(`Failed to load document: ${response.status}`);
      }

      selectedDocument = await response.json();

      // Cache the document for future use
      if (selectedDocument) {
        documentCache.set(doc.id, selectedDocument);
        parsedContent = marked.parse(selectedDocument.content) as string;
        // Check if it's a PDF document and set view mode accordingly
        isPdfDocument = selectedDocument.file_type === "application/pdf";
        viewMode = isPdfDocument ? "pdf" : "raw";

        // Load chunk data for highlighting if needed
        await loadChunkDataForHighlighting();
      }
    } catch (error) {
      console.error("Failed to load document:", error);
      showPushNotification("Failed to load document", "error");
    } finally {
      documentLoading = false;
    }
  }

  function formatDate(dateString: string) {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function getSourceIcon(sourceType: string) {
    switch (sourceType) {
      case "chat":
        return "💬";
      case "file":
        return "📄";
      case "url":
        return "🌐";
      default:
        return "📋";
    }
  }

  $: filteredDocuments = (() => {
    console.log(
      "Filtering documents. Selected folder:",
      selectedFolder?.name,
      selectedFolder?.id
    );
    console.log("Total documents:", internalDocuments.length);
    console.log(
      "All documents folder_ids:",
      internalDocuments.map((d) => ({
        title: d.title,
        folder_id: (d as any).folder_id,
      }))
    );

    const filtered = internalDocuments.filter((doc) => {
      // First apply search filter
      const matchesSearch =
        !searchQuery ||
        doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        doc.source_type.toLowerCase().includes(searchQuery.toLowerCase());

      if (!matchesSearch) return false;

      // Then apply folder filter if a folder is selected
      if (selectedFolder) {
        const docFolderId = (doc as any).folder_id;
        const selectedFolderId = selectedFolder.id;
        const matches = docFolderId === selectedFolderId;

        console.log(
          "Checking doc:",
          doc.title,
          "docFolderId:",
          docFolderId,
          "selectedFolderId:",
          selectedFolderId,
          "matches:",
          matches
        );

        return matches;
      }

      // If no folder is selected, show all documents
      return true;
    });

    console.log("Filtered documents:", filtered.length);
    return filtered;
  })();

  function showPushNotification(
    message: string,
    type: "success" | "error" | "info" | "processing" = "info",
    duration: number = 3000
  ) {
    const id = ++notificationId;
    pushNotifications = [...pushNotifications, { id, message, type, duration }];

    // Return ID so we can remove specific notifications
    return id;
  }

  function removePushNotification(id: number) {
    pushNotifications = pushNotifications.filter((n) => n.id !== id);
  }

  async function enterEditMode() {
    if (!selectedDocument) return;

    isEditMode = true;
    documentLoading = true;

    try {
      // Use direct API call through proxy (same pattern as chat loading)
      const response = await fetch(
        `/api/v1/documents/${selectedDocument.id}/chunks`
      );

      if (!response.ok) {
        throw new Error(`Failed to load chunks: ${response.status}`);
      }

      // Direct JSON parsing - no SvelteKit serialization issues
      selectedDocumentChunks = await response.json();
      console.log("Document chunks loaded:", selectedDocumentChunks);

      editedChunks = JSON.parse(
        JSON.stringify(selectedDocumentChunks?.chunks || [])
      ); // Deep clone
      editedTitle = selectedDocumentChunks?.title || "";

      // Combine all chunks into single content for unified editing
      editedContent = editedChunks.map((chunk) => chunk.content).join("\n\n");

      hasChanges = false;
    } catch (error) {
      console.error("Failed to load document chunks:", error);
      showPushNotification("Failed to load document for editing", "error");
      isEditMode = false;
    } finally {
      documentLoading = false;
    }
  }

  function exitEditMode() {
    isEditMode = false;
    selectedDocumentChunks = null;
    editedChunks = [];
    editedTitle = "";
    editedContent = "";
    hasChanges = false;
  }

  function closeDocument() {
    selectedDocument = null;
    viewMode = "raw";
    isPdfDocument = false;
    chunkData = [];
    highlightedContent = "";
  }

  async function loadChunkDataForHighlighting() {
    if (!selectedDocument || !highlightChunks.length) {
      highlightedContent = selectedDocument?.content || "";
      return;
    }

    try {
      const chunkUrl = `/api/v1/documents/${selectedDocument.id}/chunks?chunk_ids=${highlightChunks.join(",")}`;
      console.log("Loading chunk data for highlighting:", chunkUrl);

      const response = await fetch(chunkUrl, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          "Content-Type": "application/json",
        },
      });

      if (response.ok) {
        const data = await response.json();
        chunkData = data.chunks || [];
        console.log("Loaded chunk data:", chunkData);

        // Apply highlights to raw content
        if (selectedDocument.content) {
          highlightedContent = highlightTextInRaw(
            selectedDocument.content,
            chunkData
          );
        }
      } else {
        console.error("Failed to load chunk data:", response.status);
        highlightedContent = selectedDocument?.content || "";
      }
    } catch (err) {
      console.error("Error loading chunk data:", err);
      highlightedContent = selectedDocument?.content || "";
    }
  }

  function highlightTextInRaw(content: string, chunks: any[]): string {
    if (!chunks.length) return content;

    let highlightedText = content;

    // Sort chunks by content length (longest first) to avoid partial matches
    const sortedChunks = [...chunks].sort((a, b) => {
      const aText = a.content || a.chunk_text || a.text || "";
      const bText = b.content || b.chunk_text || b.text || "";
      return bText.length - aText.length;
    });

    sortedChunks.forEach((chunk, index) => {
      const chunkText = chunk.content || chunk.chunk_text || chunk.text || "";
      if (!chunkText.trim()) return;

      // Use fuzzy matching - look for the chunk text (allowing for minor variations)
      const normalizedChunkText = chunkText.toLowerCase().trim();
      const normalizedContent = highlightedText.toLowerCase();

      // Find the chunk text in the content
      const chunkIndex = normalizedContent.indexOf(normalizedChunkText);

      if (chunkIndex !== -1) {
        // Get the actual text from the original content (preserving case)
        const actualText = highlightedText.substring(
          chunkIndex,
          chunkIndex + chunkText.length
        );

        // Replace with highlighted version
        const highlightedChunk = `<mark class="chunk-highlight" data-chunk-id="${chunk.id}" data-chunk-index="${index}">${actualText}</mark>`;

        highlightedText =
          highlightedText.substring(0, chunkIndex) +
          highlightedChunk +
          highlightedText.substring(chunkIndex + chunkText.length);
      }
    });

    return highlightedText;
  }

  function handleContentEdit(html: string, markdown: string) {
    if (editedContent !== markdown) {
      editedContent = markdown;
      hasChanges = true;
    }
  }

  function handleTitleEdit(newTitle: string) {
    if (editedTitle !== newTitle) {
      editedTitle = newTitle;
      hasChanges = true;
    }
  }

  async function saveChanges() {
    if (!selectedDocument || !hasChanges) return;

    const savingNotificationId = showPushNotification(
      "Saving changes...",
      "processing",
      0
    );

    try {
      // Split the unified content back into chunks
      // We'll use a simple strategy: split by double newlines or by max chunk size
      const chunkSize = 1500; // Approximate chunk size in characters
      const paragraphs = editedContent.split("\n\n");
      const newChunks = [];
      let currentChunk = "";

      for (const paragraph of paragraphs) {
        if (
          (currentChunk + "\n\n" + paragraph).length > chunkSize &&
          currentChunk.length > 0
        ) {
          // Save current chunk and start new one
          newChunks.push({
            content: currentChunk.trim(),
            id: editedChunks[newChunks.length]?.id, // Keep existing ID if available
          });
          currentChunk = paragraph;
        } else {
          // Add to current chunk
          currentChunk = currentChunk
            ? currentChunk + "\n\n" + paragraph
            : paragraph;
        }
      }

      // Don't forget the last chunk
      if (currentChunk.trim()) {
        newChunks.push({
          content: currentChunk.trim(),
          id: editedChunks[newChunks.length]?.id,
        });
      }

      // Use direct API call through proxy (same pattern as chat operations)
      const response = await fetch(
        `/api/v1/documents/${selectedDocument.id}/chunks`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            title: editedTitle,
            chunks: newChunks, // Send all chunks (full replacement)
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to save: ${response.status}`);
      }

      const result = await response.json();
      console.log("Update result:", result);

      removePushNotification(savingNotificationId);
      showPushNotification("Document updated successfully!", "success");

      // Clear cache for this document since it was updated
      if (selectedDocument) {
        documentCache.delete(selectedDocument.id);
      }

      // Reload the document to show updated content
      await selectDocument(selectedDocument);
      exitEditMode();

      // Refresh document list to update title if changed
      await loadDocuments();
    } catch (error) {
      console.error("Failed to save changes:", error);
      removePushNotification(savingNotificationId);
      showPushNotification("Failed to save changes", "error");
    }
  }

  async function moveUploadedDocumentToFolder(
    uploadId: string,
    folderId: string
  ) {
    // Wait for document processing to complete before attempting to move
    let attempts = 0;
    const maxAttempts = 20; // 20 attempts * 3 seconds = 60 seconds max wait

    while (attempts < maxAttempts) {
      await new Promise((resolve) => setTimeout(resolve, 3000)); // Wait 3 seconds

      try {
        // Reload documents to check if the uploaded document is available
        await loadDocuments();

        // Find the uploaded document by upload_id in metadata
        const uploadedDoc = internalDocuments.find((doc) => {
          const metadata = doc.metadata || {};
          return metadata.upload_id === uploadId;
        });

        if (uploadedDoc) {
          // Document is ready, move it to the folder
          const url = new URL(
            `/api/v1/documents/${uploadedDoc.id}/move`,
            window.location.origin
          );
          url.searchParams.set("folder_id", folderId);

          const response = await fetch(url.toString(), {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
            },
          });

          if (response.ok) {
            await loadDocuments();
            await loadFolders();
            return; // Success, exit the function
          }
        }
      } catch (error) {
        console.log(`Attempt ${attempts + 1} failed:`, error);
      }

      attempts++;
    }

    // If we get here, moving failed after all attempts
    console.warn(
      `Failed to move uploaded document ${uploadId} to folder ${folderId} after ${maxAttempts} attempts`
    );
  }

  async function moveUploadedDocumentToFolderByFilename(
    filename: string,
    folderId: string
  ) {
    // Wait for document processing to complete before attempting to move
    let attempts = 0;
    const maxAttempts = 30; // 30 attempts * 2 seconds = 60 seconds max wait

    console.log(
      `Looking for uploaded document with filename: ${filename} to move to folder: ${folderId}`
    );

    while (attempts < maxAttempts) {
      // Start checking immediately for first attempt, then wait 2 seconds
      if (attempts > 0) {
        await new Promise((resolve) => setTimeout(resolve, 2000)); // Wait 2 seconds
      }

      try {
        // Reload documents to check if the uploaded document is available
        await loadDocuments();

        // Find the uploaded document by filename and recent creation
        // Sort by creation date and look for matching filename in the most recent documents
        const recentDocuments = internalDocuments
          .sort(
            (a, b) =>
              new Date(b.created_at).getTime() -
              new Date(a.created_at).getTime()
          )
          .slice(0, 10); // Look at the 10 most recent documents

        const uploadedDoc = recentDocuments.find((doc) => {
          // Remove file extension from filename for better matching
          const baseFilename = filename.replace(/\.[^/.]+$/, "");
          const docTitle = doc.title.replace(/\.[^/.]+$/, "");

          // Check if filename matches in multiple ways
          const exactTitleMatch = doc.title === filename;
          const baseNameMatch = docTitle === baseFilename;
          const titleContainsFilename = doc.title.includes(baseFilename);
          const filenameContainsTitle = baseFilename.includes(docTitle);

          // Check metadata for original filename
          const metadata = doc.metadata || {};
          const metadataFilename =
            metadata.original_filename || metadata.filename;
          const exactMetadataMatch = metadataFilename === filename;

          // Check if document is not already in a folder (to avoid moving wrong docs)
          const notInFolder = !doc.folder_id;

          // Document should be recent (within last 5 minutes)
          const docAge = Date.now() - new Date(doc.created_at).getTime();
          const isRecent = docAge < 5 * 60 * 1000; // 5 minutes

          const matchesFilename =
            exactTitleMatch ||
            baseNameMatch ||
            titleContainsFilename ||
            filenameContainsTitle ||
            exactMetadataMatch;

          console.log(
            `Checking doc "${doc.title}": exactTitleMatch=${exactTitleMatch}, baseNameMatch=${baseNameMatch}, titleContainsFilename=${titleContainsFilename}, exactMetadataMatch=${exactMetadataMatch}, notInFolder=${notInFolder}, isRecent=${isRecent}, age=${Math.round(docAge / 1000)}s`
          );

          return matchesFilename && notInFolder && isRecent;
        });

        if (uploadedDoc) {
          console.log(
            `Found document to move: ${uploadedDoc.title} (${uploadedDoc.id})`
          );

          // Document is ready, move it to the folder
          const url = new URL(
            `/api/v1/documents/${uploadedDoc.id}/move`,
            window.location.origin
          );
          url.searchParams.set("folder_id", folderId);

          const response = await fetch(url.toString(), {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
            },
          });

          if (response.ok) {
            console.log(
              `Successfully moved document "${uploadedDoc.title}" to folder ${folderId}`
            );
            await loadDocuments();
            await loadFolders();
            return; // Success, exit the function
          } else {
            console.error(`Failed to move document: ${response.status}`);
          }
        } else {
          console.log(
            `Document with filename "${filename}" not found yet (attempt ${attempts + 1})`
          );
          console.log(
            `Available recent documents:`,
            recentDocuments.map((d) => ({
              title: d.title,
              created_at: d.created_at,
              folder_id: d.folder_id,
              age_seconds: Math.round(
                (Date.now() - new Date(d.created_at).getTime()) / 1000
              ),
            }))
          );
        }
      } catch (error) {
        console.log(`Attempt ${attempts + 1} failed:`, error);
      }

      attempts++;
    }

    // If we get here, moving failed after all attempts
    console.warn(
      `Failed to move uploaded document "${filename}" to folder ${folderId} after ${maxAttempts} attempts`
    );
  }

  // Drag and drop functions
  function handleDocumentDragStart(event: DragEvent, doc: Document) {
    draggedDocument = doc;
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", doc.id);
    }
  }

  function handleDocumentDragEnd(event: DragEvent) {
    draggedDocument = null;
    dropTargetFolder = null;
  }

  function handleFolderDragOver(event: DragEvent, folderId: string) {
    event.preventDefault();
    if (draggedDocument && event.dataTransfer) {
      event.dataTransfer.dropEffect = "move";
      dropTargetFolder = folderId;
    }
  }

  function handleFolderDragLeave(event: DragEvent) {
    dropTargetFolder = null;
  }

  async function handleFolderDrop(event: DragEvent, folderId: string) {
    event.preventDefault();
    dropTargetFolder = null;

    if (!draggedDocument) return;

    try {
      const url = new URL(
        `/api/v1/documents/${draggedDocument.id}/move`,
        window.location.origin
      );
      url.searchParams.set("folder_id", folderId);

      const response = await fetch(url.toString(), {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (response.ok) {
        await loadDocuments();
        await loadFolders(); // Refresh folder document counts
        showPushNotification(`Document moved to folder`, "success");
      } else {
        const errorData = await response.text();
        console.error("Move document error:", response.status, errorData);
        throw new Error(
          `Failed to move document: ${response.status} - ${errorData}`
        );
      }
    } catch (error) {
      console.error("Failed to move document:", error);
      showPushNotification("Failed to move document", "error");
    }

    draggedDocument = null;
  }

  // Handle dropping on root (no folder)
  async function handleRootDrop(event: DragEvent) {
    event.preventDefault();
    dropTargetFolder = null;

    if (!draggedDocument) return;

    try {
      const url = new URL(
        `/api/v1/documents/${draggedDocument.id}/move`,
        window.location.origin
      );
      // Don't set folder_id to move to root

      const response = await fetch(url.toString(), {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (response.ok) {
        await loadDocuments();
        await loadFolders();
        showPushNotification(`Document moved to root`, "success");
      } else {
        const errorData = await response.text();
        console.error("Move document error:", response.status, errorData);
        throw new Error(
          `Failed to move document: ${response.status} - ${errorData}`
        );
      }
    } catch (error) {
      console.error("Failed to move document:", error);
      showPushNotification("Failed to move document", "error");
    }

    draggedDocument = null;
  }

  // Helper function to extract folder structure from uploaded files
  function extractFolderStructure(files: File[]) {
    const folderMap = new Map();

    files.forEach((file) => {
      // webkitRelativePath contains the full path including folder names
      const relativePath = (file as any).webkitRelativePath || file.name;
      const pathParts = relativePath.split("/");

      // Skip the file name, only process folder parts
      const folderParts = pathParts.slice(0, -1);

      if (folderParts.length > 0) {
        // Build nested folder structure
        let currentPath = "";
        folderParts.forEach((folderName, index) => {
          const parentPath = currentPath;
          currentPath = currentPath
            ? `${currentPath}/${folderName}`
            : folderName;

          if (!folderMap.has(currentPath)) {
            folderMap.set(currentPath, {
              name: folderName,
              fullPath: currentPath,
              parentPath: parentPath || null,
              level: index,
            });
          }
        });
      }
    });

    return Object.fromEntries(folderMap);
  }

  // Create folder structure in the backend
  async function createFolderStructure(folderStructure) {
    const folderMapping = new Map(); // Maps full path to folder ID
    const foldersByLevel = {};

    // Group folders by level for proper creation order (parents first)
    Object.values(folderStructure).forEach((folder) => {
      if (!foldersByLevel[folder.level]) {
        foldersByLevel[folder.level] = [];
      }
      foldersByLevel[folder.level].push(folder);
    });

    // Create folders level by level
    const levels = Object.keys(foldersByLevel).sort(
      (a, b) => parseInt(a) - parseInt(b)
    );

    for (const level of levels) {
      const foldersAtLevel = foldersByLevel[level];

      for (const folder of foldersAtLevel) {
        try {
          // Determine parent folder ID
          let parentId = selectedUploadFolder; // Base folder selected by user

          if (folder.parentPath) {
            parentId =
              folderMapping.get(folder.parentPath) || selectedUploadFolder;
          }

          // Create folder via API
          const response = await fetch("/api/v1/folders/", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              name: folder.name,
              description: `Folder from upload: ${folder.fullPath}`,
              color: "#4F46E5", // Default blue color
              parent_id: parentId,
            }),
          });

          if (response.ok) {
            const createdFolder = await response.json();
            folderMapping.set(folder.fullPath, createdFolder.id);
            console.log(`Created folder: ${folder.name} (${createdFolder.id})`);
          } else {
            console.error(
              `Failed to create folder ${folder.name}:`,
              response.status
            );
            // Use parent folder as fallback
            folderMapping.set(folder.fullPath, parentId);
          }
        } catch (error) {
          console.error(`Error creating folder ${folder.name}:`, error);
          // Use parent folder as fallback
          folderMapping.set(folder.fullPath, selectedUploadFolder);
        }
      }
    }

    return folderMapping;
  }

  // Process files with folder assignments
  async function processFilesWithFolders(
    files: File[],
    folderMapping: Map<string, string>
  ) {
    if (files.length === 0) return;

    // Validate files (same as processFiles)
    const allowedTypes = [
      "application/pdf",
      "text/plain",
      "text/markdown",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ];
    const maxSize = 50 * 1024 * 1024; // 50MB

    const validFiles: File[] = [];
    for (const file of files) {
      if (!allowedTypes.includes(file.type)) {
        showPushNotification(
          `"${file.name}" - Unsupported file type. Supported: PDF, TXT, MD, DOCX`,
          "error"
        );
        continue;
      }
      if (file.size > maxSize) {
        showPushNotification(
          `"${file.name}" - File too large. Maximum size is 50MB.`,
          "error"
        );
        continue;
      }
      validFiles.push(file);
    }

    if (validFiles.length === 0) return;

    uploadLoading = true;
    uploadedFiles = validFiles;

    // Show processing notification
    const processingNotificationId = showPushNotification(
      `Uploading ${validFiles.length} file${validFiles.length > 1 ? "s" : ""} with folder structure...`,
      "processing",
      0
    );

    try {
      let successCount = 0;
      let failCount = 0;

      for (let i = 0; i < validFiles.length; i++) {
        const file = validFiles[i];
        uploadProgress[file.name] = {
          progress: (i / validFiles.length) * 100,
          status: "uploading",
        };

        try {
          const formData = new FormData();
          formData.append("file", file);

          const fetchResponse = await fetch("/api/v1/documents/upload", {
            method: "POST",
            body: formData,
          });

          if (!fetchResponse.ok) {
            throw new Error(`Upload failed for ${file.name}`);
          }

          const uploadResult = await fetchResponse.json();

          uploadProgress[file.name] = {
            progress: 100,
            status: "completed",
          };
          successCount++;

          // Determine target folder for this file
          const relativePath = (file as any).webkitRelativePath || file.name;
          const pathParts = relativePath.split("/");
          const folderParts = pathParts.slice(0, -1); // Remove filename

          let targetFolderId = selectedUploadFolder; // Default to user-selected folder

          if (folderParts.length > 0) {
            const fileFolderPath = folderParts.join("/");
            targetFolderId =
              folderMapping.get(fileFolderPath) || selectedUploadFolder;
          }

          // Move the document to the correct folder if needed
          if (targetFolderId) {
            // Use filename to identify the document after upload
            await moveUploadedDocumentToFolderByFilename(
              file.name,
              targetFolderId
            );
          }
        } catch (error) {
          uploadProgress[file.name] = {
            progress: 100,
            status: "failed",
          };
          failCount++;
          console.error(`Failed to upload ${file.name}:`, error);
        }
      }

      if (successCount > 0) {
        showPushNotification(
          `Successfully uploaded ${successCount} file${successCount > 1 ? "s" : ""} with folder structure${failCount > 0 ? `, ${failCount} failed` : ""}`,
          "success",
          3000
        );
      } else {
        showPushNotification(`Failed to upload files`, "error", 3000);
      }

      // Remove processing notification
      removePushNotification(processingNotificationId);

      // Close modal
      showUploadModal = false;
      uploadedFiles = [];
      uploadProgress = {};

      // Refresh everything
      await loadFolders();
      await loadDocuments();
    } catch (error) {
      console.error("Failed to upload folder:", error);
      removePushNotification(processingNotificationId);
      showPushNotification("Failed to upload folder", "error", 5000);
    } finally {
      uploadLoading = false;
      uploadedFiles = [];
      uploadProgress = {};
    }
  }

  async function handleFileUpload(event: Event) {
    const target = event.target as HTMLInputElement;
    const files = target.files;

    if (!files || files.length === 0) return;

    // Convert FileList to Array and filter out system files
    const originalFileCount = files.length;
    const fileArray = Array.from(files).filter((file) => {
      const fileName = file.name.toLowerCase();
      const systemFiles = [
        ".ds_store",
        "thumbs.db",
        "desktop.ini",
        ".localized",
        "__macosx",
      ];

      // Filter out system files and hidden files starting with ._
      return (
        !systemFiles.includes(fileName) &&
        !fileName.startsWith("._") &&
        !fileName.startsWith(".tmp")
      );
    });

    // Notify user if system files were filtered out
    const filteredCount = originalFileCount - fileArray.length;
    if (filteredCount > 0) {
      console.log(
        `Filtered out ${filteredCount} system files (.DS_Store, etc.)`
      );
      showPushNotification(
        `Filtered out ${filteredCount} system file${filteredCount > 1 ? "s" : ""} (.DS_Store, etc.)`,
        "info",
        3000
      );
    }

    if (fileArray.length === 0) {
      showPushNotification("No valid files selected", "error");
      return;
    }

    await processFiles(fileArray);

    // Reset file input
    if (target) {
      target.value = "";
    }
  }

  async function handleFolderUpload(event: Event) {
    const target = event.target as HTMLInputElement;
    const files = target.files;

    if (!files || files.length === 0) return;

    // Convert FileList to Array and filter out system files
    const originalFileCount = files.length;
    const fileArray = Array.from(files).filter((file) => {
      const fileName = file.name.toLowerCase();
      const systemFiles = [
        ".ds_store",
        "thumbs.db",
        "desktop.ini",
        ".localized",
        "__macosx",
      ];

      // Filter out system files and hidden files starting with ._
      return (
        !systemFiles.includes(fileName) &&
        !fileName.startsWith("._") &&
        !fileName.startsWith(".tmp")
      );
    });

    // Notify user if system files were filtered out
    const filteredCount = originalFileCount - fileArray.length;
    if (filteredCount > 0) {
      console.log(
        `Filtered out ${filteredCount} system files (.DS_Store, etc.)`
      );
      showPushNotification(
        `Filtered out ${filteredCount} system file${filteredCount > 1 ? "s" : ""} (.DS_Store, etc.)`,
        "info",
        3000
      );
    }

    if (fileArray.length === 0) {
      showPushNotification("No valid files found in folder", "error");
      return;
    }

    // Extract folder structure from file paths
    const folderStructure = extractFolderStructure(fileArray);

    console.log("Folder structure to create:", folderStructure);

    // Show notification about folder upload
    showPushNotification(
      `Uploading folder with ${fileArray.length} files across ${Object.keys(folderStructure).length} folders...`,
      "info"
    );

    try {
      // First, create the folder structure
      const folderMapping = await createFolderStructure(folderStructure);

      console.log("Created folder mapping:", Object.fromEntries(folderMapping));

      // Then upload files and assign them to the correct folders
      await processFilesWithFolders(fileArray, folderMapping);
    } catch (error) {
      console.error("Failed to upload folder:", error);
      showPushNotification("Failed to upload folder", "error");
    }

    // Reset file input
    if (target) {
      target.value = "";
    }
  }

  async function processFiles(files: File[]) {
    if (files.length === 0) return;

    // Validate files
    const allowedTypes = [
      "application/pdf",
      "text/plain",
      "text/markdown",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ];
    const maxSize = 50 * 1024 * 1024; // 50MB

    const validFiles: File[] = [];
    for (const file of files) {
      if (!allowedTypes.includes(file.type)) {
        showPushNotification(
          `"${file.name}" - Unsupported file type. Supported: PDF, TXT, MD, DOCX`,
          "error"
        );
        continue;
      }
      if (file.size > maxSize) {
        showPushNotification(
          `"${file.name}" - File too large. Maximum size is 50MB.`,
          "error"
        );
        continue;
      }
      validFiles.push(file);
    }

    if (validFiles.length === 0) return;

    // Add to uploading files list for placeholder UI
    const newUploads = validFiles.map((file) => ({
      name: file.name,
      id: nextUploadId++,
    }));
    uploadingFiles = [...uploadingFiles, ...newUploads];

    uploadLoading = true;
    uploadedFiles = validFiles;

    // Show processing notification
    const processingNotificationId = showPushNotification(
      `Uploading ${validFiles.length} file${validFiles.length > 1 ? "s" : ""}...`,
      "processing",
      0
    ); // Duration 0 = stays until removed

    try {
      // Process files in parallel if multiple or use single upload for one file
      if (validFiles.length === 1) {
        // Single file upload
        const formData = new FormData();
        formData.append("file", validFiles[0]);

        const fetchResponse = await fetch("/api/v1/documents/upload", {
          method: "POST",
          body: formData,
        });

        if (!fetchResponse.ok) {
          throw new Error(
            `Upload failed: ${fetchResponse.status} ${fetchResponse.statusText}`
          );
        }

        const response = await fetchResponse.json();
        showPushNotification(
          `"${validFiles[0].name}" uploaded! Processing in background...`,
          "success",
          3000
        );

        // If a folder is selected, move the document after processing completes
        if (selectedUploadFolder) {
          await moveUploadedDocumentToFolder(
            response.upload_id,
            selectedUploadFolder
          );
        }
      } else {
        // Multiple file upload - upload sequentially to show progress
        let successCount = 0;
        let failCount = 0;

        for (let i = 0; i < validFiles.length; i++) {
          const file = validFiles[i];
          uploadProgress[file.name] = {
            progress: (i / validFiles.length) * 100,
            status: "uploading",
          };

          try {
            const formData = new FormData();
            formData.append("file", file);

            const fetchResponse = await fetch("/api/v1/documents/upload", {
              method: "POST",
              body: formData,
            });

            if (!fetchResponse.ok) {
              throw new Error(`Upload failed for ${file.name}`);
            }

            const uploadResult = await fetchResponse.json();

            uploadProgress[file.name] = {
              progress: 100,
              status: "completed",
            };
            successCount++;

            // If a folder is selected, move the document after processing completes
            if (selectedUploadFolder) {
              await moveUploadedDocumentToFolder(
                uploadResult.upload_id,
                selectedUploadFolder
              );
            }
          } catch (error) {
            uploadProgress[file.name] = {
              progress: 100,
              status: "failed",
            };
            failCount++;
            console.error(`Failed to upload ${file.name}:`, error);
          }
        }

        if (successCount > 0) {
          showPushNotification(
            `Successfully uploaded ${successCount} file${successCount > 1 ? "s" : ""}${failCount > 0 ? `, ${failCount} failed` : ""}`,
            "success",
            3000
          );
        } else {
          showPushNotification(`Failed to upload files`, "error", 3000);
        }
      }

      // Remove processing notification
      removePushNotification(processingNotificationId);

      // Close modal
      showUploadModal = false;
      uploadedFiles = [];
      uploadProgress = {};

      // Wait a bit then refresh document list to see if processing is complete
      setTimeout(async () => {
        await loadDocuments();
        showPushNotification(`Document processing complete!`, "success", 3000);
      }, 5000); // Check after 5 seconds

      // Continue checking periodically
      const checkInterval = setInterval(async () => {
        await loadDocuments();
      }, 3000);

      // Stop checking after 30 seconds
      setTimeout(() => clearInterval(checkInterval), 30000);
    } catch (error) {
      console.error("Failed to upload documents:", error);
      removePushNotification(processingNotificationId);
      showPushNotification("Failed to upload documents", "error", 5000);
    } finally {
      uploadLoading = false;
      uploadedFiles = [];
      uploadProgress = {};
    }
  }

  function handleDragOver(event: DragEvent) {
    event.preventDefault();
    isDragging = true;
  }

  function handleDragLeave(event: DragEvent) {
    event.preventDefault();
    isDragging = false;
  }

  async function handleDrop(event: DragEvent) {
    event.preventDefault();
    isDragging = false;

    const items = event.dataTransfer?.items;
    if (!items || items.length === 0) return;

    // Check if any of the dropped items is a folder
    let hasFolder = false;
    const allFiles: File[] = [];

    // Convert DataTransferItemList to array for easier processing
    const itemsArray = Array.from(items);

    for (const item of itemsArray) {
      if (item.kind === "file") {
        const entry = item.webkitGetAsEntry();
        if (entry && entry.isDirectory) {
          hasFolder = true;
          // Recursively read folder contents
          const folderFiles = await readDirectory(entry);
          allFiles.push(...folderFiles);
        } else {
          const file = item.getAsFile();
          if (file) {
            allFiles.push(file);
          }
        }
      }
    }

    // Filter out system files
    const originalFileCount = allFiles.length;
    const fileArray = allFiles.filter((file) => {
      const fileName = file.name.toLowerCase();
      const systemFiles = [
        ".ds_store",
        "thumbs.db",
        "desktop.ini",
        ".localized",
        "__macosx",
      ];

      // Filter out system files and hidden files starting with ._
      return (
        !systemFiles.includes(fileName) &&
        !fileName.startsWith("._") &&
        !fileName.startsWith(".tmp")
      );
    });

    // Notify user if system files were filtered out
    const filteredCount = originalFileCount - fileArray.length;
    if (filteredCount > 0) {
      console.log(
        `Filtered out ${filteredCount} system files (.DS_Store, etc.)`
      );
      showPushNotification(
        `Filtered out ${filteredCount} system file${filteredCount > 1 ? "s" : ""} (.DS_Store, etc.)`,
        "info",
        3000
      );
    }

    if (fileArray.length === 0) {
      showPushNotification("No valid files dropped", "error");
      return;
    }

    // If folder was dropped, process with folder structure
    if (hasFolder) {
      // Extract folder structure from file paths
      const folderStructure = extractFolderStructure(fileArray);

      console.log("Folder structure to create:", folderStructure);

      // Show notification about folder upload
      showPushNotification(
        `Uploading folder with ${fileArray.length} files across ${Object.keys(folderStructure).length} folders...`,
        "info"
      );

      try {
        // First, create the folder structure
        const folderMapping = await createFolderStructure(folderStructure);

        console.log(
          "Created folder mapping:",
          Object.fromEntries(folderMapping)
        );

        // Then upload files and assign them to the correct folders
        await processFilesWithFolders(fileArray, folderMapping);
      } catch (error) {
        console.error("Failed to upload folder:", error);
        showPushNotification("Failed to upload folder", "error");
      }
    } else {
      // Regular file upload
      await processFiles(fileArray);
    }
  }

  // Helper function to recursively read directory contents
  async function readDirectory(entry: any): Promise<File[]> {
    const files: File[] = [];

    if (entry.isFile) {
      return new Promise((resolve) => {
        entry.file((file: File) => {
          // Add webkitRelativePath manually
          const relativePath = entry.fullPath.substring(1); // Remove leading slash
          Object.defineProperty(file, "webkitRelativePath", {
            value: relativePath,
            writable: false,
          });
          resolve([file]);
        });
      });
    } else if (entry.isDirectory) {
      const dirReader = entry.createReader();

      return new Promise((resolve) => {
        const readEntries = () => {
          dirReader.readEntries(async (entries: any[]) => {
            if (entries.length === 0) {
              resolve(files);
            } else {
              for (const childEntry of entries) {
                const childFiles = await readDirectory(childEntry);
                files.push(...childFiles);
              }
              readEntries(); // Continue reading (directories might have more than 100 entries)
            }
          });
        };
        readEntries();
      });
    }

    return files;
  }

  function confirmDeleteDocument(doc: DocumentDetail) {
    documentToDelete = doc;
    showDeleteModal = true;
  }

  async function deleteDocument() {
    if (!documentToDelete) return;

    const deletingNotificationId = showPushNotification(
      `Deleting "${documentToDelete.title}"...`,
      "processing",
      0
    );

    try {
      const response = await fetch(`/api/v1/documents/${documentToDelete.id}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error(
          `Delete failed: ${response.status} ${response.statusText}`
        );
      }

      removePushNotification(deletingNotificationId);
      showPushNotification(
        `"${documentToDelete.title}" deleted successfully`,
        "success",
        3000
      );

      // Clear from cache if it exists
      documentCache.delete(documentToDelete.id);

      // Clear selected document if it was the one being deleted
      if (selectedDocument?.id === documentToDelete.id) {
        closeDocument();
      }

      // Close delete modal
      showDeleteModal = false;
      documentToDelete = null;

      // Refresh document list
      await loadDocuments();
    } catch (error) {
      console.error("Failed to delete document:", error);
      removePushNotification(deletingNotificationId);
      showPushNotification("Failed to delete document", "error", 5000);
    }
  }
</script>

<div class="flex h-full w-full bg-white rounded-xl shadow-lg overflow-hidden">
  <!-- Document List -->
  <div class="w-80 border-r border-gray-200 flex flex-col h-full">
    <!-- Fixed Header -->
    <div class="p-4 border-b border-gray-200 bg-white z-10 flex-shrink-0">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-lg font-semibold text-gray-800">Knowledge Base</h2>
        <button
          on:click={() => dispatch("close")}
          class="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
          title="Back to Chat"
        >
          <svg
            class="w-5 h-5 text-gray-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            ></path>
          </svg>
        </button>
      </div>

      <!-- Action Buttons -->
      <div class="flex gap-2 mb-3">
        <button
          on:click={() => {
            selectedUploadFolder = selectedFolder?.id || null;
            showUploadModal = true;
          }}
          class="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white rounded-lg transition-all duration-200 text-sm font-medium shadow-md hover:shadow-lg"
        >
          <svg
            class="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          Upload
        </button>
        <button
          on:click={() => (showCreateFolderModal = true)}
          class="px-3 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-colors text-sm font-medium shadow-md hover:shadow-lg"
          title="Create Folder"
        >
          <svg
            class="w-4 h-4"
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
        </button>
      </div>
      <input
        type="text"
        placeholder="Search documents..."
        bind:value={searchQuery}
        class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
      />
    </div>

    <!-- Scrollable Content -->
    <div class="flex-1 overflow-y-auto custom-scrollbar min-h-0">
      {#if isLoading}
        <div class="flex items-center justify-center h-64 text-gray-500">
          <div
            class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"
          ></div>
        </div>
      {:else if internalDocuments.length === 0 && uploadingFiles.length === 0 && folders.length === 0}
        <div class="text-center py-12 px-4 text-gray-500">
          <div class="text-4xl mb-3">📚</div>
          <div class="text-sm font-medium">No documents found</div>
          <div class="text-xs mt-1">
            Save chats to build your knowledge base
          </div>
        </div>
      {:else}
        {#each uploadingFiles as file}
          <div
            class="w-full px-4 py-3 text-left border-b border-gray-100 opacity-60 pointer-events-none"
          >
            <div class="flex items-start gap-3">
              <div class="text-xl mt-0.5">📄</div>
              <div class="flex-1 min-w-0">
                <div class="font-medium text-sm text-gray-900 truncate">
                  {file.name}
                </div>
                <div class="flex items-center gap-2 mt-1 text-xs text-gray-500">
                  <div
                    class="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-500"
                  ></div>
                  <span>Uploading...</span>
                </div>
              </div>
            </div>
          </div>
        {/each}

        <!-- Folder Structure + Root entry -->
        <div class="space-y-1">
          <!-- All Documents / Root Level (drag/drop target) -->
          <div
            class="w-full px-4 py-2 hover:bg-gray-50 transition-colors text-left flex items-center gap-2 {!selectedFolder
              ? 'bg-blue-50 text-blue-700'
              : ''} {dropTargetFolder === 'root'
              ? 'bg-green-100 border-2 border-dashed border-green-500'
              : ''}"
            on:dragover={(e) => {
              e.preventDefault();
              if (draggedDocument) dropTargetFolder = "root";
            }}
            on:dragleave={() => {
              dropTargetFolder = null;
            }}
            on:drop={handleRootDrop}
          >
            <button
              on:click={() => selectFolder(null)}
              class="flex items-center gap-2 flex-1"
            >
              <svg
                class="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                />
              </svg>
              <span class="font-medium">All Documents</span>
              <span class="text-xs text-gray-500 ml-auto"
                >{internalDocuments.length}</span
              >
            </button>
          </div>

          <!-- Folders -->
          {#each folders as folder}
            <div class="folder-item group">
              <div
                class="w-full flex items-center hover:bg-gray-50 transition-colors {selectedFolder?.id ===
                folder.id
                  ? 'bg-blue-50 text-blue-700'
                  : ''} {dropTargetFolder === folder.id
                  ? 'bg-green-100 border-2 border-dashed border-green-500'
                  : ''}"
                style="padding-left: {16 + 0 * 16}px"
                on:dragover={(e) => handleFolderDragOver(e, folder.id)}
                on:dragleave={handleFolderDragLeave}
                on:drop={(e) => handleFolderDrop(e, folder.id)}
              >
                <button
                  on:click={() => toggleFolderExpansion(folder.id)}
                  class="p-1 hover:bg-gray-200 rounded transition-colors mr-1"
                >
                  <svg
                    class="w-3 h-3 transform transition-transform {expandedFolders.has(
                      folder.id
                    )
                      ? 'rotate-90'
                      : ''}"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </button>
                <button
                  on:click={() => selectFolder(folder)}
                  class="flex-1 py-2 text-left flex items-center gap-2 min-w-0"
                >
                  {#if expandedFolders.has(folder.id)}
                    <FolderOpen class="w-4 h-4" style="color: {folder.color}" />
                  {:else}
                    <Folder class="w-4 h-4" style="color: {folder.color}" />
                  {/if}
                  <span class="font-medium truncate">{folder.name}</span>
                  <span class="text-xs text-gray-500 ml-auto"
                    >{folder.document_count}</span
                  >
                </button>
                <button
                  on:click|stopPropagation={() => showDeleteFolder(folder)}
                  class="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 rounded transition-all mr-1"
                  title="Delete folder"
                >
                  <svg
                    class="w-3 h-3 text-red-600"
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

              {#if expandedFolders.has(folder.id)}
                {#each folder.children as childFolder}
                  <div class="folder-item group">
                    <div
                      class="w-full flex items-center hover:bg-gray-50 transition-colors {selectedFolder?.id ===
                      childFolder.id
                        ? 'bg-blue-50 text-blue-700'
                        : ''} {dropTargetFolder === childFolder.id
                        ? 'bg-green-100 border-2 border-dashed border-green-500'
                        : ''}"
                      style="padding-left: {16 + 1 * 16}px"
                      on:dragover={(e) =>
                        handleFolderDragOver(e, childFolder.id)}
                      on:dragleave={handleFolderDragLeave}
                      on:drop={(e) => handleFolderDrop(e, childFolder.id)}
                    >
                      <button
                        on:click={() => selectFolder(childFolder)}
                        class="flex-1 py-2 text-left flex items-center gap-2 min-w-0"
                      >
                        <Folder
                          class="w-4 h-4"
                          style="color: {childFolder.color}"
                        />
                        <span class="font-medium truncate"
                          >{childFolder.name}</span
                        >
                        <span class="text-xs text-gray-500 ml-auto"
                          >{childFolder.document_count}</span
                        >
                      </button>
                      <button
                        on:click|stopPropagation={() =>
                          showDeleteFolder(childFolder)}
                        class="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 rounded transition-all mr-1"
                        title="Delete folder"
                      >
                        <svg
                          class="w-3 h-3 text-red-600"
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
                {/each}
              {/if}
            </div>
          {/each}

          <!-- Documents in Selected Folder -->
          {#if selectedFolder || filteredDocuments.length > 0}
            <div class="border-t border-gray-200 mt-2 pt-2">
              <div
                class="px-4 py-1 text-xs text-gray-500 font-medium uppercase tracking-wide"
              >
                {selectedFolder
                  ? `Documents in ${selectedFolder.name}`
                  : "All Documents"}
              </div>
              {#if filteredDocuments.length === 0}
                <div class="text-center py-8 px-4 text-gray-500">
                  <div class="text-2xl mb-2">📄</div>
                  <div class="text-sm">
                    {selectedFolder
                      ? "No documents in this folder"
                      : "No documents found"}
                  </div>
                </div>
              {:else}
                {#each filteredDocuments as doc}
                  <div
                    class="relative group"
                    draggable="true"
                    on:dragstart={(e) => handleDocumentDragStart(e, doc)}
                    on:dragend={handleDocumentDragEnd}
                  >
                    <button
                      on:click={() => selectDocument(doc)}
                      class="w-full px-4 py-3 hover:bg-gray-50 transition-colors text-left border-b border-gray-100 {selectedDocument?.id ===
                      doc.id
                        ? 'bg-blue-50'
                        : ''} {draggedDocument?.id === doc.id
                        ? 'opacity-50'
                        : ''}"
                    >
                      <div class="flex items-start gap-3">
                        <div
                          class="opacity-0 group-hover:opacity-100 transition-opacity mt-1"
                        >
                          <svg
                            class="w-3 h-3 text-gray-400"
                            fill="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"
                            />
                          </svg>
                        </div>
                        <div class="text-lg mt-0.5">
                          {getSourceIcon(doc.source_type)}
                        </div>
                        <div class="flex-1 min-w-0">
                          <div
                            class="font-medium text-sm text-gray-900 truncate"
                          >
                            {doc.title}
                          </div>
                          <div
                            class="flex items-center gap-2 mt-1 text-xs text-gray-500"
                          >
                            <span class="capitalize">{doc.source_type}</span>
                            <span>•</span>
                            <span>{doc.chunk_count} chunks</span>
                          </div>
                          <div class="text-xs text-gray-400 mt-1">
                            {formatDate(doc.created_at)}
                          </div>
                        </div>
                        {#if selectedDocument?.id === doc.id}
                          <div
                            class="w-1 h-12 bg-blue-500 rounded-full self-center"
                          ></div>
                        {/if}
                      </div>
                    </button>

                    <button
                      on:click|stopPropagation={() => showMoveDocument(doc)}
                      class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1 bg-white hover:bg-gray-100 rounded shadow-sm border transition-all"
                      title="Move to folder"
                    >
                      <svg
                        class="w-4 h-4 text-gray-600"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M13 13l3-3m0 0l-3 3m3-3H8m13 0a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                    </button>
                  </div>
                {/each}
              {/if}
            </div>
          {/if}
        </div>
      {/if}
    </div>

    <!-- Fixed Footer -->
    <div
      class="p-3 border-t border-gray-200 text-center text-xs text-gray-500 bg-white flex-shrink-0"
    >
      {filteredDocuments.length} document{filteredDocuments.length !== 1
        ? "s"
        : ""} in knowledge base
    </div>
  </div>

  <!-- Document Viewer -->
  <div class="flex-1 flex flex-col h-full">
    {#if documentLoading}
      <div class="flex-1 flex items-center justify-center">
        <div class="text-center">
          <div
            class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"
          ></div>
          <div class="text-sm text-gray-500">Loading document...</div>
        </div>
      </div>
    {:else if selectedDocument}
      <div class="flex flex-col h-full">
        <!-- Document Header -->
        <div class="px-6 py-4 border-b border-gray-200 flex-shrink-0">
          <div class="flex items-start justify-between">
            <div class="flex-1">
              {#if isEditMode}
                <input
                  type="text"
                  bind:value={editedTitle}
                  on:input={(e) => handleTitleEdit(e.currentTarget.value)}
                  class="text-xl font-semibold text-gray-900 bg-transparent border-b-2 border-blue-500 focus:outline-none w-full"
                />
              {:else}
                <h3 class="text-xl font-semibold text-gray-900">
                  {selectedDocument.title}
                </h3>
              {/if}
              <div class="flex items-center gap-3 mt-2 text-sm text-gray-500">
                <span class="flex items-center gap-1">
                  {getSourceIcon(selectedDocument.source_type)}
                  <span class="capitalize">{selectedDocument.source_type}</span>
                </span>
                <span>•</span>
                <span
                  >{selectedDocument.chunk_count}
                  chunks</span
                >
                <span>•</span>
                <span>{formatDate(selectedDocument.created_at)}</span>
              </div>
            </div>
            <div class="flex items-center gap-2">
              {#if !isEditMode}
                <button
                  on:click={enterEditMode}
                  class="px-4 py-2 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors font-medium shadow-sm"
                  title="Edit document"
                >
                  Edit
                </button>
                <button
                  on:click={() =>
                    selectedDocument && confirmDeleteDocument(selectedDocument)}
                  class="px-4 py-2 text-sm bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors font-medium shadow-sm"
                  title="Delete document"
                >
                  Delete
                </button>
              {/if}
              <button
                on:click={() => {
                  if (isEditMode) {
                    exitEditMode();
                  } else {
                    closeDocument();
                  }
                }}
                class="p-1 hover:bg-gray-100 rounded-lg transition-colors"
                title={isEditMode ? "Cancel editing" : "Close document"}
              >
                <svg
                  class="w-5 h-5 text-gray-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M6 18L18 6M6 6l12 12"
                  ></path>
                </svg>
              </button>
            </div>
          </div>

          <!-- View Toggle -->
          {#if !isEditMode}
            <div class="mt-3 flex items-center gap-3">
              <span class="text-sm text-gray-600">View:</span>
              <div class="flex items-center gap-2 bg-gray-100 rounded-lg p-1">
                {#if isPdfDocument}
                  <button
                    on:click={() => (viewMode = "raw")}
                    class="px-3 py-1 text-sm rounded-md transition-colors {viewMode ===
                    'raw'
                      ? 'bg-white text-blue-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-800'}"
                  >
                    Raw
                  </button>
                  <button
                    on:click={() => (viewMode = "pdf")}
                    class="px-3 py-1 text-sm rounded-md transition-colors {viewMode ===
                    'pdf'
                      ? 'bg-white text-blue-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-800'}"
                  >
                    PDF
                  </button>
                {:else}
                  <button
                    on:click={() => (displayMode = "formatted")}
                    class="px-3 py-1 text-sm rounded-md transition-colors {displayMode ===
                    'formatted'
                      ? 'bg-white text-blue-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-800'}"
                  >
                    Formatted
                  </button>
                  <button
                    on:click={() => (displayMode = "raw")}
                    class="px-3 py-1 text-sm rounded-md transition-colors {displayMode ===
                    'raw'
                      ? 'bg-white text-blue-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-800'}"
                  >
                    Raw Markdown
                  </button>
                {/if}
              </div>
            </div>
          {/if}

          <!-- Tags Section -->
          <div class="mt-3">
            <TagSelector
              documentId={selectedDocument.id}
              mode="edit"
              on:error={(e) => showPushNotification(e.detail.message, "error")}
              on:createTag={(e) => {
                // Dispatch event to parent to switch to tag management
                dispatch("switchToTags", {
                  tagName: e.detail.name,
                });
              }}
            />
          </div>
        </div>

        <!-- Document Content -->
        <div
          class="flex-1 overflow-y-auto bg-white custom-scrollbar min-h-0 relative {viewMode ===
          'pdf'
            ? 'p-0'
            : 'px-6 py-4'}"
        >
          {#if isEditMode}
            <!-- Display mode toggle for edit mode -->
            <div
              class="mb-4 flex items-center gap-3 sticky top-0 bg-white pb-2 border-b border-gray-200 z-10"
            >
              <span class="text-sm text-gray-600">View:</span>
              <div class="flex items-center gap-2 bg-gray-100 rounded-lg p-1">
                <button
                  on:click={() => (displayMode = "formatted")}
                  class="px-3 py-1 text-sm rounded-md transition-colors {displayMode ===
                  'formatted'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-800'}"
                >
                  Formatted
                </button>
                <button
                  on:click={() => (displayMode = "raw")}
                  class="px-3 py-1 text-sm rounded-md transition-colors {displayMode ===
                  'raw'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-800'}"
                >
                  Raw
                </button>
              </div>
              <span class="text-xs text-gray-500 ml-auto">
                {editedContent.length}
                characters
              </span>
            </div>

            {#if displayMode === "formatted"}
              <!-- TipTap Editor (without instructional text) -->
              <div class="space-y-3">
                <TipTapEditor
                  content={editedContent}
                  onChange={handleContentEdit}
                  placeholder="Start writing your document..."
                  height="500px"
                  editable={true}
                />
              </div>
            {:else}
              <!-- Raw markdown view -->
              <div class="space-y-3">
                <div class="text-xs text-gray-500">
                  Edit raw markdown syntax. Use **bold**, *italic*, # headings,
                  etc.
                </div>
                <textarea
                  value={editedContent}
                  on:input={(e) => handleContentEdit("", e.currentTarget.value)}
                  class="w-full p-4 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                  placeholder="Enter markdown content..."
                  style="height: 500px;"
                />
              </div>
            {/if}
          {:else if !isEditMode}
            {#if viewMode === "pdf" && isPdfDocument && selectedDocument}
              <!-- PDF Viewer -->
              <iframe
                src={`/api/v1/documents/${selectedDocument.id}/pdf`}
                class="absolute inset-0 w-full h-full border-0"
                title="PDF Viewer"
              />
            {:else if displayMode === "raw"}
              <!-- Raw markdown display (read-only) with highlighting -->
              {#if highlightChunks.length > 0}
                <pre
                  class="w-full p-4 bg-gray-50 border border-gray-200 rounded-lg font-mono text-sm whitespace-pre-wrap overflow-x-auto">{@html highlightedContent}</pre>
              {:else}
                <pre
                  class="w-full p-4 bg-gray-50 border border-gray-200 rounded-lg font-mono text-sm whitespace-pre-wrap overflow-x-auto">{selectedDocument?.content ||
                    ""}</pre>
              {/if}
            {:else}
              <!-- Formatted markdown content -->
              <div
                class="markdown-content prose prose-sm max-w-none
								prose-headings:text-gray-900
								prose-p:text-gray-700
								prose-strong:text-gray-900
								prose-code:text-pink-600 prose-code:bg-gray-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded
								prose-pre:bg-gray-900 prose-pre:text-gray-100
								prose-blockquote:border-l-4 prose-blockquote:border-blue-500 prose-blockquote:bg-blue-50 prose-blockquote:text-gray-700
								prose-a:text-blue-600 prose-a:no-underline hover:prose-a:underline
								prose-li:text-gray-700
								prose-hr:border-gray-300"
              >
                {@html parsedContent}
              </div>
            {/if}
          {:else}
            <div class="flex items-center justify-center h-full">
              <div
                class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"
              ></div>
            </div>
          {/if}
        </div>

        <!-- Document Actions -->
        <div
          class="px-6 py-3 border-t border-gray-200 flex items-center justify-between flex-shrink-0"
        >
          <div class="text-xs text-gray-500">
            {#if isEditMode && hasChanges}
              <span class="text-orange-600 font-medium">Unsaved changes</span>
            {:else}
              Document ID: {selectedDocument.id.slice(0, 8)}...
            {/if}
          </div>
          <div class="flex gap-2">
            {#if isEditMode}
              <button
                on:click={exitEditMode}
                class="px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                on:click={saveChanges}
                disabled={!hasChanges}
                class="px-3 py-1.5 text-xs rounded-lg transition-colors {hasChanges
                  ? 'bg-blue-500 hover:bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'}"
              >
                Save Changes
              </button>
            {:else}
              <button
                class="px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
                title="Copy content"
                on:click={() => {
                  navigator.clipboard.writeText(
                    selectedDocument?.content || ""
                  );
                }}
              >
                Copy Content
              </button>
            {/if}
          </div>
        </div>
      </div>
    {:else}
      <div class="flex-1 flex items-center justify-center text-gray-400">
        <div class="text-center">
          <div class="text-6xl mb-4">📖</div>
          <div class="text-lg font-medium">Select a document to view</div>
          <div class="text-sm mt-2">
            Choose from your knowledge base on the left
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>

<!-- Create Folder Modal -->
{#if showCreateFolderModal}
  <div
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
  >
    <div class="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4">
      <div class="p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-gray-800">Create Folder</h3>
          <button
            on:click={() => resetCreateFolderModal()}
            class="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg
              class="w-5 h-5 text-gray-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              ></path>
            </svg>
          </button>
        </div>

        <form on:submit|preventDefault={createFolder} class="space-y-4">
          <div>
            <label
              for="folderName"
              class="block text-sm font-medium text-gray-700 mb-2"
              >Folder Name</label
            >
            <input
              id="folderName"
              type="text"
              bind:value={newFolderName}
              placeholder="Enter folder name..."
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label
              for="folderDescription"
              class="block text-sm font-medium text-gray-700 mb-2"
              >Description (optional)</label
            >
            <textarea
              id="folderDescription"
              bind:value={newFolderDescription}
              placeholder="Enter description..."
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows="2"
            ></textarea>
          </div>

          <div class="flex gap-4">
            <div class="flex-1">
              <label
                for="folderColor"
                class="block text-sm font-medium text-gray-700 mb-2"
                >Color</label
              >
              <div class="flex items-center gap-2">
                <input
                  id="folderColor"
                  type="color"
                  bind:value={newFolderColor}
                  class="w-8 h-8 border border-gray-300 rounded cursor-pointer"
                />
                <span class="text-sm text-gray-600">{newFolderColor}</span>
              </div>
            </div>

            <div class="flex-1">
              <label
                for="folderParent"
                class="block text-sm font-medium text-gray-700 mb-2"
                >Parent Folder</label
              >
              <select
                id="folderParent"
                bind:value={newFolderParentId}
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={null}>Root (No parent)</option>
                {#each folders as folder}
                  <option value={folder.id}>{folder.name}</option>
                {/each}
              </select>
            </div>
          </div>

          <div class="flex justify-end gap-2 pt-2">
            <button
              type="button"
              on:click={() => resetCreateFolderModal()}
              class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              class="px-4 py-2 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors font-medium"
            >
              Create Folder
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
{/if}

<!-- Move Document Modal -->
{#if showMoveDocumentModal && documentToMove}
  <div
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
  >
    <div class="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4">
      <div class="p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-gray-800">Move Document</h3>
          <button
            on:click={() => resetMoveDocumentModal()}
            class="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg
              class="w-5 h-5 text-gray-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              ></path>
            </svg>
          </button>
        </div>

        <div class="mb-4">
          <p class="text-sm text-gray-600 mb-2">Moving document:</p>
          <div class="p-3 bg-gray-50 rounded-lg">
            <div class="flex items-center gap-2">
              <div class="text-lg">
                {getSourceIcon(documentToMove.source_type)}
              </div>
              <div class="font-medium text-gray-900">
                {documentToMove.title}
              </div>
            </div>
          </div>
        </div>

        <form on:submit|preventDefault={moveDocument} class="space-y-4">
          <div>
            <label
              for="targetFolder"
              class="block text-sm font-medium text-gray-700 mb-2"
              >Move to Folder</label
            >
            <select
              id="targetFolder"
              bind:value={targetFolderId}
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={null}>Root (No folder)</option>
              {#each folders as folder}
                <option value={folder.id}>
                  {folder.name}
                </option>
                {#each folder.children as childFolder}
                  <option value={childFolder.id}>
                    &nbsp;&nbsp;{childFolder.name}
                  </option>
                {/each}
              {/each}
            </select>
          </div>

          <div class="flex justify-end gap-2 pt-2">
            <button
              type="button"
              on:click={() => resetMoveDocumentModal()}
              class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              class="px-4 py-2 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors font-medium"
            >
              Move Document
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
{/if}

<!-- Upload Modal -->
{#if showUploadModal}
  <div
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
  >
    <div class="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4">
      <div class="p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-gray-800">Upload Documents</h3>
          <button
            on:click={() => {
              showUploadModal = false;
              selectedUploadFolder = null;
            }}
            class="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg
              class="w-5 h-5 text-gray-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              ></path>
            </svg>
          </button>
        </div>

        <!-- Folder Selection -->
        <div class="mb-4">
          <label
            for="uploadTargetFolder"
            class="block text-sm font-medium text-gray-700 mb-2"
          >
            Upload to folder (optional)
          </label>
          <select
            id="uploadTargetFolder"
            bind:value={selectedUploadFolder}
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
          >
            <option value={null}>Root (No folder)</option>
            {#each folders as folder}
              <option value={folder.id}>{folder.name}</option>
              {#each folder.children as childFolder}
                <option value={childFolder.id}
                  >&nbsp;&nbsp;{childFolder.name}</option
                >
              {/each}
            {/each}
          </select>
        </div>

        <div
          class="border-2 border-dashed rounded-lg p-8 text-center transition-colors {isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300'}"
          on:dragover={handleDragOver}
          on:dragleave={handleDragLeave}
          on:drop={handleDrop}
        >
          <!-- File inputs -->
          <input
            type="file"
            id="fileUpload"
            accept=".pdf,.txt,.md,.docx"
            multiple
            on:change={handleFileUpload}
            class="hidden"
            disabled={uploadLoading}
          />
          <input
            type="file"
            id="folderUpload"
            webkitdirectory
            multiple
            on:change={handleFolderUpload}
            class="hidden"
            disabled={uploadLoading}
          />

          {#if uploadLoading}
            <div
              class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"
            ></div>
            <p class="text-sm text-gray-600 mb-3">
              Uploading {uploadedFiles.length}
              file{uploadedFiles.length > 1 ? "s" : ""}...
            </p>
            {#if Object.keys(uploadProgress).length > 0}
              <div class="space-y-2 max-h-48 overflow-y-auto">
                {#each Object.entries(uploadProgress) as [filename, progress]}
                  <div class="text-xs text-left">
                    <div class="flex items-center justify-between mb-1">
                      <span class="truncate flex-1">{filename}</span>
                      <span class="ml-2">
                        {#if progress.status === "completed"}
                          ✓
                        {:else if progress.status === "failed"}
                          ✗
                        {:else}
                          {Math.round(progress.progress)}%
                        {/if}
                      </span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-1.5">
                      <div
                        class="h-1.5 rounded-full transition-all {progress.status ===
                        'failed'
                          ? 'bg-red-500'
                          : progress.status === 'completed'
                            ? 'bg-green-500'
                            : 'bg-blue-500'}"
                        style="width: {progress.progress}%"
                      ></div>
                    </div>
                  </div>
                {/each}
              </div>
            {/if}
          {:else}
            <svg
              class="w-12 h-12 text-gray-400 mx-auto mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <p class="text-sm text-gray-600 mb-2">
              {isDragging
                ? "Drop files here"
                : "Drag & drop files here or click to browse"}
            </p>
            <p class="text-xs text-gray-500 mb-4">
              Supports PDF, TXT, MD, and DOCX files (max 50MB each). Folder
              upload preserves directory structure.
            </p>
            <div class="flex gap-2 justify-center">
              <label
                for="fileUpload"
                class="inline-flex items-center px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium rounded-lg cursor-pointer transition-colors"
              >
                <svg
                  class="w-4 h-4 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  ></path>
                </svg>
                Select Files
              </label>
              <label
                for="folderUpload"
                class="inline-flex items-center px-4 py-2 bg-green-500 hover:bg-green-600 text-white text-sm font-medium rounded-lg cursor-pointer transition-colors"
              >
                <svg
                  class="w-4 h-4 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                  ></path>
                </svg>
                Select Folder
              </label>
            </div>
          {/if}
        </div>

        <div class="flex justify-end gap-2 mt-6">
          <button
            on:click={() => {
              showUploadModal = false;
              selectedUploadFolder = null;
            }}
            class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
            disabled={uploadLoading}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- Delete Confirmation Modal -->
{#if showDeleteModal && documentToDelete}
  <div
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
  >
    <div class="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4">
      <div class="p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-gray-800">Delete Document</h3>
          <button
            on:click={() => {
              showDeleteModal = false;
              documentToDelete = null;
            }}
            class="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg
              class="w-5 h-5 text-gray-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              ></path>
            </svg>
          </button>
        </div>

        <div class="mb-6">
          <div class="flex items-center gap-3 mb-3">
            <div
              class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center"
            >
              <svg
                class="w-6 h-6 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                ></path>
              </svg>
            </div>
            <div>
              <p class="text-sm text-gray-600">
                Are you sure you want to delete this document?
              </p>
              <p class="font-medium text-gray-900 mt-1">
                "{documentToDelete.title}"
              </p>
            </div>
          </div>
          <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <p class="text-sm text-yellow-800">
              <strong>Warning:</strong> This action cannot be undone. The document
              and all its content will be permanently removed from your knowledge
              base.
            </p>
          </div>
        </div>

        <div class="flex justify-end gap-3">
          <button
            on:click={() => {
              showDeleteModal = false;
              documentToDelete = null;
            }}
            class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            on:click={deleteDocument}
            class="px-4 py-2 text-sm bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors font-medium"
          >
            Delete Document
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- Delete Folder Confirmation Modal -->
{#if showDeleteFolderModal && folderToDelete}
  <div
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
  >
    <div class="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4">
      <div class="p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-gray-800">Delete Folder</h3>
          <button
            on:click={() => resetDeleteFolderModal()}
            class="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg
              class="w-5 h-5 text-gray-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              ></path>
            </svg>
          </button>
        </div>

        <div class="mb-6">
          <div class="flex items-center gap-3 mb-3">
            <div
              class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center"
            >
              <svg
                class="w-6 h-6 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                ></path>
              </svg>
            </div>
            <div>
              <p class="text-sm text-gray-600">
                Are you sure you want to delete this folder?
              </p>
              <p class="font-medium text-gray-900 mt-1">
                "{folderToDelete.name}"
              </p>
            </div>
          </div>
          <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <p class="text-sm text-yellow-800">
              <strong>Warning:</strong> This will delete the folder and move all
              its contents
              {folderToDelete.parent_id
                ? "to the parent folder"
                : "to the root level"}. Child folders and documents will not be
              deleted, only reorganized.
            </p>
          </div>
        </div>

        <div class="flex justify-end gap-3">
          <button
            on:click={() => resetDeleteFolderModal()}
            class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            on:click={deleteFolder}
            class="px-4 py-2 text-sm bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors font-medium"
          >
            Delete Folder
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- Push Notifications -->
{#each pushNotifications as notification (notification.id)}
  <PushNotification
    message={notification.message}
    type={notification.type}
    duration={notification.duration}
    onClose={() => removePushNotification(notification.id)}
  />
{/each}

<style>
  /* Custom scrollbar styling */
  :global(.custom-scrollbar) {
    scrollbar-width: thin;
    scrollbar-color: #cbd5e1 #f1f5f9;
  }

  :global(.custom-scrollbar::-webkit-scrollbar) {
    width: 8px;
    height: 8px;
  }

  :global(.custom-scrollbar::-webkit-scrollbar-track) {
    background: #f1f5f9;
    border-radius: 4px;
  }

  :global(.custom-scrollbar::-webkit-scrollbar-thumb) {
    background: #cbd5e1;
    border-radius: 4px;
  }

  :global(.custom-scrollbar::-webkit-scrollbar-thumb:hover) {
    background: #94a3b8;
  }

  :global(.markdown-content pre) {
    background-color: #1a1a1a;
    color: #e0e0e0;
    padding: 1rem;
    border-radius: 0.5rem;
    overflow-x: auto;
  }

  :global(.markdown-content code) {
    font-family: "Monaco", "Courier New", monospace;
  }

  :global(.markdown-content pre code) {
    background-color: transparent;
    color: inherit;
    padding: 0;
  }

  :global(.markdown-content h1),
  :global(.markdown-content h2),
  :global(.markdown-content h3) {
    font-weight: 600;
    margin-top: 1.5rem;
    margin-bottom: 0.75rem;
  }

  :global(.markdown-content p) {
    line-height: 1.7;
    margin-bottom: 1rem;
  }

  :global(.markdown-content ul),
  :global(.markdown-content ol) {
    margin-left: 1.5rem;
    margin-bottom: 1rem;
  }

  :global(.markdown-content li) {
    margin-bottom: 0.5rem;
  }

  :global(.markdown-content blockquote) {
    padding: 0.75rem 1rem;
    margin: 1rem 0;
    border-left: 4px solid #3b82f6;
    background-color: #eff6ff;
  }

  /* Chunk highlighting styles */
  :global(.chunk-highlight) {
    background-color: rgba(255, 255, 0, 0.3);
    padding: 2px 4px;
    border-radius: 3px;
    font-weight: inherit;
    font-style: normal;
  }
</style>
