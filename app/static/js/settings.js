document.addEventListener("DOMContentLoaded", () => {

    const wargameSelect = document.getElementById("wargame-select");
    const factionSelect = document.getElementById("faction-select");
    const addFactionButton = document.getElementById("add-faction");
    const selectedFactionsList = document.getElementById("selected-factions-list");
    const selectedFactionInputs = document.getElementById("selected-faction-inputs");
    const noFactions = document.getElementById("no-factions");

    const saveFactionsBtn = document.getElementById("save-factions-btn");
    const factionsForm = document.getElementById("factions-form");

    const selectedFactionIds = new Set();


    function attachRemoveHandler(item, factionId) {
        const removeButton = item.querySelector(".remove-faction");

        if (!removeButton) {
            return;
        }

        removeButton.addEventListener("click", () => {
            selectedFactionIds.delete(factionId);
            item.remove();
            removeHiddenInput(factionId);
            updateEmptyMessage();
            updateFactionSelect();

            // Показываем кнопку сохранения
            if (saveFactionsBtn) {
                saveFactionsBtn.style.display = "inline-flex";
                window.hasUnsavedChanges = true;
            }
        });
    }


    function initSelectedFactions() {
        const items = selectedFactionsList.querySelectorAll(".selected-faction");

        for (const item of items) {
            const factionId = Number(item.dataset.factionId);

            if (!factionId) {
                continue;
            }

            selectedFactionIds.add(factionId);
            attachRemoveHandler(item, factionId);
        }
    }


    function getFactionsForWargame(wargameId) {
        return factionsByWargame[wargameId] || [];
    }


    function updateFactionSelect() {
        const wargameId = wargameSelect.value;
        factionSelect.innerHTML = "";

        if (!wargameId) {
            const option = document.createElement("option");
            option.value = "";
            option.textContent = "Сначала выберите варгейм";
            factionSelect.appendChild(option);
            factionSelect.disabled = true;
            addFactionButton.disabled = true;
            return;
        }

        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = "Выберите фракцию";
        factionSelect.appendChild(placeholder);

        const factions = getFactionsForWargame(wargameId);

        for (const faction of factions) {
            if (selectedFactionIds.has(faction.id)) {
                continue;
            }

            const option = document.createElement("option");
            option.value = faction.id;
            option.textContent = faction.faction_name;
            factionSelect.appendChild(option);
        }

        const hasOptions = factionSelect.options.length > 1;
        factionSelect.disabled = !hasOptions;
        addFactionButton.disabled = !hasOptions;
    }


    function getWargameName(wargameId) {
        const option = Array.from(wargameSelect.options).find(
            item => item.value === String(wargameId)
        );

        return option ? option.textContent.trim() : "Неизвестный варгейм";
    }


    function addFactionTag(faction) {
        const listItem = document.createElement("li");
        listItem.className = "selected-faction";
        listItem.dataset.factionId = faction.id;

        const name = document.createElement("span");
        name.className = "selected-faction-name";
        name.textContent = faction.faction_name;

        const wargame = document.createElement("span");
        wargame.className = "selected-faction-wargame";
        wargame.textContent = `(${getWargameName(faction.wargameId)})`;

        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.className = "remove-faction";
        removeButton.textContent = "Удалить";

        listItem.appendChild(name);
        listItem.appendChild(wargame);
        listItem.appendChild(removeButton);

        selectedFactionsList.appendChild(listItem);
        attachRemoveHandler(listItem, faction.id);
    }


    function addHiddenInput(factionId) {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = "faction_ids";
        input.value = factionId;
        input.dataset.factionId = factionId;
        selectedFactionInputs.appendChild(input);
    }


    function removeHiddenInput(factionId) {
        const input = selectedFactionInputs.querySelector(
            `input[data-faction-id="${factionId}"]`
        );

        if (input) {
            input.remove();
        }
    }


    function updateEmptyMessage() {
        if (selectedFactionIds.size === 0) {
            noFactions.style.display = "block";
        } else {
            noFactions.style.display = "none";
        }
    }


    if (addFactionButton) {
        addFactionButton.addEventListener("click", () => {
            const factionId = Number(factionSelect.value);

            if (!factionId || selectedFactionIds.has(factionId)) {
                return;
            }

            const faction = getFactionsForWargame(wargameSelect.value).find(
                item => item.id === factionId
            );

            if (!faction) {
                return;
            }

            selectedFactionIds.add(factionId);
            addHiddenInput(factionId);
            addFactionTag(faction);
            updateEmptyMessage();
            updateFactionSelect();

            // Показываем кнопку сохранения
            if (saveFactionsBtn) {
                saveFactionsBtn.style.display = "inline-flex";
                window.hasUnsavedChanges = true;
            }
        });
    }

    if (wargameSelect) {
        wargameSelect.addEventListener("change", updateFactionSelect);
    }

    if (factionsForm) {
        factionsForm.addEventListener("submit", () => {
            window.hasUnsavedChanges = false;
        });
    }

    if (selectedFactionsList) {
        initSelectedFactions();
        updateFactionSelect();
        updateEmptyMessage();
    }

    const avatarInput = document.getElementById("avatar-input");
    const previewContainer = document.getElementById("avatar-preview-container");
    const saveAvatarBtn = document.getElementById("save-avatar-btn");

    if (avatarInput && previewContainer) {

        avatarInput.addEventListener("change", (event) => {
            const file = event.target.files[0];

            if (!file) {
                return;
            }

            const reader = new FileReader();

            reader.onload = (e) => {
                previewContainer.innerHTML = "";

                const img = document.createElement("img");
                img.src = e.target.result;
                img.alt = "Предпросмотр";
                img.className = "settings-avatar-image";

                previewContainer.appendChild(img);
            };

            reader.readAsDataURL(file);

            // Показываем кнопку сохранения
            if (saveAvatarBtn) {
                saveAvatarBtn.style.display = "inline-flex";
                window.hasUnsavedChanges = true;
            }
        });

        const avatarForm = avatarInput.closest("form");
        if (avatarForm) {
            avatarForm.addEventListener("submit", () => {
                window.hasUnsavedChanges = false;
            });
        }
    }


    window.hasUnsavedChanges = false;

    window.addEventListener("beforeunload", (e) => {
        if (window.hasUnsavedChanges) {
            e.preventDefault();
            e.returnValue = '';
        }
    });

});