document.addEventListener("DOMContentLoaded", () => {

    const wargameSelect =
        document.getElementById("wargame-select");

    const factionSelect =
        document.getElementById("faction-select");

    const addFactionButton =
        document.getElementById("add-faction");

    const selectedFactionsList =
        document.getElementById("selected-factions-list");

    const selectedFactionInputs =
        document.getElementById("selected-faction-inputs");

    const noFactions =
        document.getElementById("no-factions");


    /*
     * ID выбранных фракций.
     *
     * Set автоматически не позволяет добавить
     * одну и ту же фракцию дважды.
     */
    const selectedFactionIds = new Set();


    /*
     * Заполняем список фракций
     * в зависимости от выбранного варгейма.
     */
    function updateFactionSelect() {

        const wargameId = wargameSelect.value;


        /*
         * Очищаем текущий список.
         */
        factionSelect.innerHTML = "";


        /*
         * Варгейм ещё не выбран.
         */
        if (!wargameId) {

            const option =
                document.createElement("option");

            option.value = "";
            option.textContent =
                "Сначала выберите варгейм";

            factionSelect.appendChild(option);

            factionSelect.disabled = true;
            addFactionButton.disabled = true;

            return;
        }


        /*
         * Получаем фракции выбранного варгейма.
         */
        const availableFactions =
            factions.filter(
                faction =>
                    String(faction.wargameId) ===
                    String(wargameId)
            );


        /*
         * Добавляем placeholder.
         */
        const placeholder =
            document.createElement("option");

        placeholder.value = "";
        placeholder.textContent =
            "Выберите фракцию";

        factionSelect.appendChild(placeholder);


        /*
         * Добавляем найденные фракции.
         */
        for (const faction of availableFactions) {

            /*
             * Если фракция уже выбрана,
             * не показываем её повторно.
             */
            if (selectedFactionIds.has(faction.id)) {
                continue;
            }


            const option =
                document.createElement("option");

            option.value = faction.id;
            option.textContent = faction.name;

            factionSelect.appendChild(option);
        }


        factionSelect.disabled =
            availableFactions.every(
                faction =>
                    selectedFactionIds.has(faction.id)
            );


        addFactionButton.disabled =
            factionSelect.disabled;
    }


    /*
     * Добавление фракции.
     */
    function addFaction() {

        const factionId =
            Number(factionSelect.value);


        if (!factionId) {
            return;
        }


        /*
         * Защита от повторного добавления.
         */
        if (selectedFactionIds.has(factionId)) {
            return;
        }


        /*
         * Находим объект фракции.
         */
        const faction =
            factions.find(
                item => item.id === factionId
            );


        if (!faction) {
            return;
        }


        /*
         * Добавляем ID в Set.
         */
        selectedFactionIds.add(factionId);


        /*
         * Создаём строку списка.
         */
        const listItem =
            document.createElement("li");

        listItem.className =
            "selected-faction";


        /*
         * Название фракции + варгейм.
         */
        const factionName =
            document.createElement("span");

        factionName.className =
            "selected-faction-name";

        factionName.textContent =
            `${faction.name} (${getWargameName(faction.wargameId)})`;


        /*
         * Кнопка удаления.
         */
        const removeButton =
            document.createElement("button");

        removeButton.type = "button";

        removeButton.className =
            "remove-faction";

        removeButton.textContent =
            "Удалить";


        /*
         * Удаление фракции.
         */
        removeButton.addEventListener(
            "click",
            () => {

                selectedFactionIds.delete(
                    factionId
                );

                listItem.remove();

                removeHiddenInput(
                    factionId
                );

                updateEmptyMessage();

                updateFactionSelect();
            }
        );


        listItem.appendChild(factionName);
        listItem.appendChild(removeButton);

        selectedFactionsList.appendChild(
            listItem
        );


        /*
         * Создаём hidden input.
         *
         * Flask получит его через:
         *
         * request.form.getlist("faction_ids")
         */
        const hiddenInput =
            document.createElement("input");

        hiddenInput.type = "hidden";

        hiddenInput.name =
            "faction_ids";

        hiddenInput.value =
            factionId;

        hiddenInput.dataset.factionId =
            factionId;


        selectedFactionInputs.appendChild(
            hiddenInput
        );


        updateEmptyMessage();

        updateFactionSelect();
    }


    /*
     * Получаем название варгейма.
     */
    function getWargameName(wargameId) {

        const option =
            wargameSelect.querySelector(
                `option[value="${wargameId}"]`
            );


        if (!option) {
            return "Неизвестный варгейм";
        }


        return option.textContent.trim();
    }


    /*
     * Удаляем hidden input.
     */
    function removeHiddenInput(factionId) {

        const input =
            selectedFactionInputs.querySelector(
                `input[data-faction-id="${factionId}"]`
            );


        if (input) {
            input.remove();
        }
    }


    /*
     * Показываем/скрываем сообщение
     * "Фракции пока не выбраны".
     */
    function updateEmptyMessage() {

        if (selectedFactionIds.size === 0) {

            noFactions.style.display =
                "block";

        } else {

            noFactions.style.display =
                "none";
        }
    }


    /*
     * Смена варгейма.
     */
    wargameSelect.addEventListener(
        "change",
        updateFactionSelect
    );


    /*
     * Добавление фракции.
     */
    addFactionButton.addEventListener(
        "click",
        addFaction
    );


    /*
     * Первоначальное состояние.
     */
    updateFactionSelect();

    updateEmptyMessage();

});