document.addEventListener("DOMContentLoaded", () => {

    const wargameSelect = document.getElementById("wargame");
    const editionSelect = document.getElementById("edition");
    const teamsContainer = document.getElementById("game-teams");
    const addTeamButton = document.getElementById("add-team");
    const gameForm = document.getElementById("game-form");

    let teamCounter = 0;


    function updateEditions() {

        const wargameId = wargameSelect.value;

        editionSelect.innerHTML = "";

        if (!wargameId) {
            const option = document.createElement("option");
            option.value = "";
            option.textContent = "Сначала выберите варгейм";
            editionSelect.appendChild(option);
            editionSelect.disabled = true;
            return;
        }

        const editions = editionsByWargame[wargameId] || [];

        if (editions.length === 0) {
            const option = document.createElement("option");
            option.value = "";
            option.textContent = "Нет редакций";
            editionSelect.appendChild(option);
            editionSelect.disabled = true;
            return;
        }

        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = "Выберите редакцию";
        editionSelect.appendChild(placeholder);

        for (const edition of editions) {
            const option = document.createElement("option");
            option.value = edition.id;
            option.textContent = edition.edition_name;
            editionSelect.appendChild(option);
        }

        editionSelect.disabled = false;
    }


    function getFactionsForWargame(wargameId) {
        return factionsByWargame[wargameId] || [];
    }


    function createPlayerBlock(teamIndex, playerIndex) {

        const block = document.createElement("div");
        block.className = "game-player";
        block.dataset.teamIndex = teamIndex;
        block.dataset.playerIndex = playerIndex;

        block.innerHTML = `
            <div class="game-player-header">
                <span class="game-player-title">
                    Игрок ${playerIndex + 1}
                </span>
                <button
                    type="button"
                    class="remove-player btn btn-secondary btn-small"
                >
                    Удалить игрока
                </button>
            </div>

            <div class="form-group">
                <label class="form-label">Ник</label>
                <input
                    type="text"
                    class="form-input player-search"
                    autocomplete="off"
                    placeholder="Начните вводить ник"
                >
                <input
                    type="hidden"
                    name="teams[${teamIndex}][players][${playerIndex}][id]"
                    class="player-id-input"
                >
                <div class="player-suggestions"></div>
            </div>

            <div class="form-group">
                <label class="form-label">Фракции</label>

                <div class="faction-add-row">
                    <select class="form-select player-faction-select">
                        <option value="">Выберите фракцию</option>
                    </select>
                    <button
                        type="button"
                        class="btn btn-secondary btn-small player-faction-add"
                    >
                        Добавить
                    </button>
                </div>

                <ul class="player-factions-list"></ul>
            </div>
        `;

        const searchInput = block.querySelector(".player-search");
        const idInput = block.querySelector(".player-id-input");
        const suggestions = block.querySelector(".player-suggestions");

        const factionSelect = block.querySelector(".player-faction-select");
        const factionAddButton = block.querySelector(".player-faction-add");
        const factionsList = block.querySelector(".player-factions-list");

        const selectedFactionIds = new Set();


        searchInput.addEventListener("input", () => {
            const query = searchInput.value.trim();
            idInput.value = "";

            if (query.length < 1) {
                suggestions.innerHTML = "";
                return;
            }

            fetch(`/games/search_players?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(players => {
                    suggestions.innerHTML = "";

                    for (const player of players) {
                        const item = document.createElement("div");
                        item.className = "player-suggestion";
                        item.textContent = player.nickname;
                        item.addEventListener("click", () => {
                            searchInput.value = player.nickname;
                            idInput.value = player.id;
                            suggestions.innerHTML = "";
                        });
                        suggestions.appendChild(item);
                    }
                });
        });


        function updateFactionSelect() {

            const factions = getFactionsForWargame(wargameSelect.value);

            factionSelect.innerHTML = "";

            const placeholder = document.createElement("option");
            placeholder.value = "";
            placeholder.textContent = "Выберите фракцию";
            factionSelect.appendChild(placeholder);

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
            factionAddButton.disabled = !hasOptions;
        }


        function addFactionTag(faction) {

            const listItem = document.createElement("li");
            listItem.className = "player-faction-tag";
            listItem.dataset.factionId = faction.id;

            const name = document.createElement("span");
            name.className = "player-faction-name";
            name.textContent = faction.faction_name;

            const removeButton = document.createElement("button");
            removeButton.type = "button";
            removeButton.className = "player-faction-remove";
            removeButton.textContent = "×";

            removeButton.addEventListener("click", () => {
                selectedFactionIds.delete(faction.id);
                listItem.remove();

                const hidden = block.querySelector(
                    `input[data-faction-id="${faction.id}"]`
                );
                if (hidden) {
                    hidden.remove();
                }

                updateFactionSelect();
            });

            listItem.appendChild(name);
            listItem.appendChild(removeButton);
            factionsList.appendChild(listItem);
        }


        block.addFactionTag = (faction) => {
            if (selectedFactionIds.has(faction.id)) {
                return;
            }

            selectedFactionIds.add(faction.id);

            const hidden = document.createElement("input");
            hidden.type = "hidden";
            hidden.name =
                `teams[${teamIndex}][players][${playerIndex}][factions][]`;
            hidden.value = faction.id;
            hidden.dataset.factionId = faction.id;
            block.appendChild(hidden);

            addFactionTag(faction);

            updateFactionSelect();
        };


        factionAddButton.addEventListener("click", () => {

            const factionId = Number(factionSelect.value);

            if (!factionId) {
                return;
            }

            if (selectedFactionIds.has(factionId)) {
                return;
            }

            const faction = getFactionsForWargame(
                wargameSelect.value
            ).find(item => item.id === factionId);

            if (!faction) {
                return;
            }

            block.addFactionTag(faction);
        });


        block.updateFactions = () => {
            selectedFactionIds.clear();

            const hiddenInputs = block.querySelectorAll(
                "input[data-faction-id]"
            );
            for (const input of hiddenInputs) {
                input.remove();
            }

            factionsList.innerHTML = "";

            updateFactionSelect();
        };


        block.querySelector(".remove-player").addEventListener("click", () => {
            block.remove();
        });


        updateFactionSelect();

        return block;
    }


    function createTeamBlock() {

        const teamIndex = teamCounter;
        teamCounter += 1;

        const block = document.createElement("div");
        block.className = "game-team";
        block.dataset.teamIndex = teamIndex;

        block.innerHTML = `
            <div class="game-team-header">
                <h3 class="game-team-title">
                    Команда ${teamIndex + 1}
                </h3>
                <button
                    type="button"
                    class="remove-team btn btn-secondary btn-small"
                >
                    Удалить команду
                </button>
            </div>

            <div class="form-group">
                <label class="form-label">Название</label>
                <input
                    type="text"
                    name="teams[${teamIndex}][name]"
                    class="form-input"
                    value="Команда ${teamIndex + 1}"
                >
            </div>

            <div class="form-group">
                <label class="form-label">Победные очки</label>
                <input
                    type="number"
                    name="teams[${teamIndex}][score]"
                    class="form-input"
                    min="0"
                >
            </div>

            <div class="form-group">
                <label class="form-label">Результат</label>
                <select
                    name="teams[${teamIndex}][result]"
                    class="form-select"
                >
                    <option value="">—</option>
                    <option value="WIN">Победа</option>
                    <option value="LOSS">Поражение</option>
                    <option value="DRAW">Ничья</option>
                </select>
            </div>

            <div class="game-team-players"></div>

            <button
                type="button"
                class="add-player btn btn-secondary btn-small"
            >
                Добавить игрока
            </button>
        `;

        const playersContainer = block.querySelector(".game-team-players");
        const addPlayerButton = block.querySelector(".add-player");
        let playerCounter = 0;

        function addPlayer() {
            const playerBlock = createPlayerBlock(
                teamIndex,
                playerCounter
            );
            playersContainer.appendChild(playerBlock);
            playerCounter += 1;
            return playerBlock;
        }

        addPlayerButton.addEventListener("click", addPlayer);

        block.querySelector(".remove-team").addEventListener("click", () => {
            block.remove();
        });

        block.addPlayer = addPlayer;
        block.updateFactions = () => {
            const playerBlocks = playersContainer.querySelectorAll(
                ".game-player"
            );
            for (const playerBlock of playerBlocks) {
                if (playerBlock.updateFactions) {
                    playerBlock.updateFactions();
                }
            }
        };

        addPlayer();

        return block;
    }


    function addTeam() {
        const teamBlock = createTeamBlock();
        teamsContainer.appendChild(teamBlock);

        if (wargameSelect.value) {
            teamBlock.updateFactions();
        }

        return teamBlock;
    }


    function parseFormData(data) {

        const TEAM_PATTERN =
            /^teams\[(\d+)\]\[(\w+)\](?:\[(\d+)\]\[(\w+)\])?(\[\])?$/;

        const teams = {};

        for (const key of Object.keys(data)) {

            const match = TEAM_PATTERN.exec(key);

            if (!match) {
                continue;
            }

            const teamIndex = parseInt(match[1], 10);
            const field = match[2];
            const playerIndex = match[3];
            const playerField = match[4];

            teams[teamIndex] = teams[teamIndex] || {};

            const team = teams[teamIndex];

            if (playerIndex === undefined) {
                team[field] = data[key];
                continue;
            }

            team.players = team.players || {};
            team.players[playerIndex] = team.players[playerIndex] || {};

            const player = team.players[playerIndex];

            if (key.endsWith("[]")) {
                player[playerField] = player[playerField] || [];

                const values = Array.isArray(data[key])
                    ? data[key]
                    : [data[key]];

                player[playerField].push(...values);
            } else {
                player[playerField] = data[key];
            }
        }

        return teams;
    }


    function restoreForm() {

        wargameSelect.value = formData["wargame"] || "";
        updateEditions();

        if (formData["edition"]) {
            editionSelect.value = formData["edition"];
        }

        const dateInput = document.getElementById("date");
        const rosterPointsInput = document.getElementById("roster_points");

        dateInput.value = formData["date"] || "";
        rosterPointsInput.value = formData["roster_points"] || "";

        const teams = parseFormData(formData);
        const teamIndices = Object.keys(teams)
            .map(Number)
            .sort((a, b) => a - b);

        if (teamIndices.length === 0) {
            addTeam();
            addTeam();
            return;
        }

        for (const teamIndex of teamIndices) {

            const teamData = teams[teamIndex];
            const teamBlock = createTeamBlock();

            teamsContainer.appendChild(teamBlock);

            const nameInput = teamBlock.querySelector(
                `input[name="teams[${teamIndex}][name]"]`
            );
            if (nameInput) {
                nameInput.value = teamData.name || "";
            }

            const scoreInput = teamBlock.querySelector(
                `input[name="teams[${teamIndex}][score]"]`
            );
            if (scoreInput) {
                scoreInput.value = teamData.score || "";
            }

            const resultSelect = teamBlock.querySelector(
                `select[name="teams[${teamIndex}][result]"]`
            );
            if (resultSelect) {
                resultSelect.value = teamData.result || "";
            }

            const playersContainer =
                teamBlock.querySelector(".game-team-players");
            playersContainer.innerHTML = "";

            const playerIndices = Object.keys(teamData.players || {})
                .map(Number)
                .sort((a, b) => a - b);

            for (const playerIndex of playerIndices) {

                const playerData = teamData.players[playerIndex];
                const playerBlock = createPlayerBlock(
                    teamIndex,
                    playerIndex
                );

                playersContainer.appendChild(playerBlock);

                const searchInput =
                    playerBlock.querySelector(".player-search");
                const idInput =
                    playerBlock.querySelector(".player-id-input");

                if (playerData.id) {
                    idInput.value = playerData.id;
                }

                if (playerData.nickname) {
                    searchInput.value = playerData.nickname;
                }

                const factionIds = playerData.factions || [];
                const factionData = getFactionsForWargame(
                    wargameSelect.value
                );

                for (const factionId of factionIds) {
                    const faction = factionData.find(
                        item => String(item.id) === String(factionId)
                    );
                    if (faction) {
                        playerBlock.addFactionTag(faction);
                    }
                }
            }

            if (playerIndices.length === 0) {
                teamBlock.addPlayer();
            }
        }
    }


    function validateForm() {

        const errors = [];

        if (!wargameSelect.value) {
            errors.push("Выберите варгейм.");
        }

        if (!editionSelect.value) {
            errors.push("Выберите редакцию.");
        }

        const dateInput = document.getElementById("date");
        const rosterPointsInput = document.getElementById("roster_points");

        if (!dateInput.value) {
            errors.push("Укажите дату партии.");
        }

        const rosterPoints = Number(rosterPointsInput.value);

        if (!rosterPointsInput.value || rosterPoints <= 0) {
            errors.push("Очки на игрока должны быть больше нуля.");
        }

        const teamBlocks = teamsContainer.querySelectorAll(".game-team");

        if (teamBlocks.length < 2) {
            errors.push("Партия должна содержать минимум 2 команды.");
        }

        const allPlayerIds = [];

        for (let i = 0; i < teamBlocks.length; i += 1) {

            const teamBlock = teamBlocks[i];
            const playerBlocks = teamBlock.querySelectorAll(".game-player");

            if (playerBlocks.length === 0) {
                errors.push(`В команде ${i + 1} нет игроков.`);
                continue;
            }

            for (let j = 0; j < playerBlocks.length; j += 1) {

                const playerBlock = playerBlocks[j];
                const idInput = playerBlock.querySelector(".player-id-input");
                const idValue = idInput ? idInput.value.trim() : "";

                if (!idValue) {
                    errors.push(
                        `В команде ${i + 1}, игрок ${j + 1}: ` +
                        `не выбран ник.`
                    );
                    continue;
                }

                allPlayerIds.push(idValue);

                const factionInputs = playerBlock.querySelectorAll(
                    "input[data-faction-id]"
                );

                if (factionInputs.length === 0) {
                    errors.push(
                        `В команде ${i + 1}, игрок ${j + 1}: ` +
                        `не выбрана ни одна фракция.`
                    );
                }
            }
        }

            const resultSelects = teamsContainer.querySelectorAll(
        'select[name$="[result]"]'
    );

    const resultValues = Array.from(resultSelects).map(
        select => select.value
    );

    const winCount = resultValues.filter(
        value => value === "WIN"
    ).length;

    const drawCount = resultValues.filter(
        value => value === "DRAW"
    ).length;

    if (winCount > 1) {
        errors.push(
            "Победителем партии может быть только одна команда."
        );
    }

    if (winCount > 0 && drawCount > 0) {
        errors.push(
            "Нельзя одновременно указать победителя и ничью."
        );
    }

    if (drawCount > 0 && drawCount !== resultValues.length) {
        errors.push(
            "Если указана ничья, её должны получить все команды."
        );
    }

    const uniqueIds = new Set(allPlayerIds);

    if (uniqueIds.size !== allPlayerIds.length) {
        errors.push("Один игрок не может участвовать в партии дважды.");
    }

    if (!uniqueIds.has(String(currentUserId))) {
        errors.push("Создатель партии должен быть её участником.");
    }

    return errors;
}


    function showClientErrors(errors) {

        const existing = document.querySelector(".client-errors");

        if (existing) {
            existing.remove();
        }

        if (errors.length === 0) {
            return;
        }

        const container = document.createElement("div");
        container.className = "form-error client-errors";

        const list = document.createElement("ul");
        list.className = "client-errors-list";

        for (const error of errors) {
            const item = document.createElement("li");
            item.textContent = error;
            list.appendChild(item);
        }

        container.appendChild(list);

        gameForm.parentNode.insertBefore(container, gameForm);

        container.scrollIntoView({
            behavior: "smooth",
            block: "start",
        });
    }


    wargameSelect.addEventListener("change", () => {
        updateEditions();

        const teamBlocks = teamsContainer.querySelectorAll(".game-team");
        for (const teamBlock of teamBlocks) {
            teamBlock.updateFactions();
        }
    });


    addTeamButton.addEventListener("click", addTeam);


    gameForm.addEventListener("submit", (event) => {
        const errors = validateForm();

        if (errors.length > 0) {
            event.preventDefault();
            showClientErrors(errors);
            return;
        }

        showClientErrors([]);
    });


    restoreForm();

});