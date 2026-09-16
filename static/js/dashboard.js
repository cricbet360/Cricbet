"use strict";

/*
|--------------------------------------------------------------------------
| CRICKBET - PROEXCH CRICKET DASHBOARD
|--------------------------------------------------------------------------
|
| This file uses ONLY:
|
|   GET /api/proexch/matches
|
| No SportMonks.
| No OddsPapi.
| No BEX.
| No SportBex.
|
|--------------------------------------------------------------------------
*/


const PROEXCH_MATCHES_URL = "/api/proexch/matches";

const REFRESH_INTERVAL = 10000;

let allMatches = [];

let currentFilter = "all";

let refreshTimer = null;

let isLoading = false;


/*
|--------------------------------------------------------------------------
| DOM HELPERS
|--------------------------------------------------------------------------
*/

function byId(id) {
    return document.getElementById(id);
}


/*
|--------------------------------------------------------------------------
| SAFE JSON
|--------------------------------------------------------------------------
*/

async function fetchJson(url, options = {}) {

    const response = await fetch(url, {
        ...options,
        headers: {
            "Accept": "application/json",
            ...(options.headers || {})
        }
    });

    let data;

    try {
        data = await response.json();
    } catch (error) {

        throw new Error(
            `Server returned invalid JSON (${response.status})`
        );
    }

    if (!response.ok) {

        let message = `HTTP ${response.status}`;

        if (data && data.detail) {
            message = data.detail;
        }

        throw new Error(message);
    }

    return data;
}


/*
|--------------------------------------------------------------------------
| PROEXCH ENVELOPE
|--------------------------------------------------------------------------
|
| Expected:
|
| {
|     "statusCode": 200,
|     "data": {
|         "data": [...]
|     }
| }
|
|--------------------------------------------------------------------------
*/

function getProExchData(payload) {

    if (!payload) {
        return null;
    }

    if (payload.statusCode !== undefined) {

        if (Number(payload.statusCode) !== 200) {

            throw new Error(
                `ProExch statusCode=${payload.statusCode}`
            );
        }
    }

    return payload.data;
}


/*
|--------------------------------------------------------------------------
| GET MATCH ARRAY
|--------------------------------------------------------------------------
*/

function getMatchesArray(payload) {

    const data = getProExchData(payload);

    if (!data) {
        return [];
    }

    if (Array.isArray(data.data)) {
        return data.data;
    }

    if (Array.isArray(data)) {
        return data;
    }

    return [];
}


/*
|--------------------------------------------------------------------------
| NORMALIZE MATCH
|--------------------------------------------------------------------------
*/

function normalizeMatch(item) {

    if (!item || typeof item !== "object") {
        return null;
    }

    const gameId =
        item.gameId ??
        item.eventId ??
        item.game_id ??
        item.event_id ??
        "";

    const marketId =
        item.marketId ??
        item.market_id ??
        "";

    const eventName =
        item.eventName ??
        item.event_name ??
        "Cricket Match";

    const eventTime =
        item.eventTime ??
        item.event_time ??
        null;

    const inPlay =
        item.inPlay ??
        item.in_play ??
        false;

    return {
        raw: item,

        gameId: String(gameId),

        marketId: String(marketId),

        eventName: String(eventName),

        eventTime: eventTime,

        inPlay: Boolean(inPlay),

        selectionId1:
            item.selectionId1 ??
            item.selection_id1 ??
            null,

        selectionId2:
            item.selectionId2 ??
            item.selection_id2 ??
            null,

        selectionId3:
            item.selectionId3 ??
            item.selection_id3 ??
            null,

        runnerName1:
            item.runnerName1 ??
            item.runner_name1 ??
            "",

        runnerName2:
            item.runnerName2 ??
            item.runner_name2 ??
            "",

        runnerName3:
            item.runnerName3 ??
            item.runner_name3 ??
            ""
    };
}


/*
|--------------------------------------------------------------------------
| LOAD MATCHES
|--------------------------------------------------------------------------
*/

async function loadMatches(showLoading = true) {

    if (isLoading) {
        return;
    }

    isLoading = true;

    const container = byId("matchesContainer");

    if (showLoading && container) {

        container.innerHTML = `
            <div class="state-box">
                <div class="loading-spinner"></div>
                Loading ProExch cricket matches...
            </div>
        `;
    }

    try {

        const payload = await fetchJson(
            PROEXCH_MATCHES_URL
        );

        const matches = getMatchesArray(payload);

        allMatches = matches
            .map(normalizeMatch)
            .filter(match => {

                return match &&
                       match.gameId &&
                       match.marketId;
            });

        renderMatches();

    } catch (error) {

        console.error(
            "ProExch match loading error:",
            error
        );

        showError(
            error.message ||
            "Unable to load ProExch cricket matches."
        );

    } finally {

        isLoading = false;
    }
}


/*
|--------------------------------------------------------------------------
| ERROR
|--------------------------------------------------------------------------
*/

function showError(message) {

    const container = byId("matchesContainer");

    if (!container) {
        return;
    }

    container.innerHTML = `
        <div class="error-box">
            <strong>Unable to load cricket matches.</strong>
            <br>
            ${escapeHtml(message)}
        </div>
    `;

    const count = byId("matchCount");

    if (count) {
        count.textContent = "ProExch connection error";
    }
}


/*
|--------------------------------------------------------------------------
| FILTER MATCHES
|--------------------------------------------------------------------------
*/

function filterMatches() {

    if (currentFilter === "live") {

        return allMatches.filter(
            match => match.inPlay === true
        );
    }

    if (currentFilter === "upcoming") {

        return allMatches.filter(
            match => match.inPlay !== true
        );
    }

    return allMatches;
}


/*
|--------------------------------------------------------------------------
| RENDER MATCHES
|--------------------------------------------------------------------------
*/

function renderMatches() {

    const container = byId("matchesContainer");

    if (!container) {
        return;
    }

    const matches = filterMatches();

    const count = byId("matchCount");

    if (count) {

        count.textContent =
            `${matches.length} match${matches.length === 1 ? "" : "es"}`;
    }

    if (!matches.length) {

        container.innerHTML = `
            <div class="state-box">
                No cricket matches found.
            </div>
        `;

        return;
    }

    container.innerHTML = matches
        .map(createMatchRow)
        .join("");

    attachMatchEvents();
}


/*
|--------------------------------------------------------------------------
| CREATE MATCH ROW
|--------------------------------------------------------------------------
*/

function createMatchRow(match) {

    const eventName = escapeHtml(
        match.eventName
    );

    const runner1 = escapeHtml(
        match.runnerName1 || "Team 1"
    );

    const runner2 = escapeHtml(
        match.runnerName2 || "Team 2"
    );

    const runner3 = escapeHtml(
        match.runnerName3 || ""
    );

    const dateText = formatDate(
        match.eventTime
    );

    const live = match.inPlay === true;

    const badge = live
        ? `<span class="live-badge">LIVE</span>`
        : `<span class="upcoming-badge">UPCOMING</span>`;

    const encodedGameId =
        encodeURIComponent(match.gameId);

    /*
     * The first row contains the match name.
     *
     * Odds are loaded on the match-details page because
     * ProExch requires both gameId and marketId.
     */

    return `
        <div
            class="match-row"
            data-game-id="${escapeHtml(match.gameId)}"
            data-market-id="${escapeHtml(match.marketId)}"
        >

            <div
                class="match-info"
                data-match-url="/match/${encodedGameId}"
            >

                <div class="match-name">
                    ${eventName}
                </div>

                <div class="match-meta">

                    ${badge}

                    <span>
                        ${runner1}
                    </span>

                    <span>
                        vs
                    </span>

                    <span>
                        ${runner2}
                    </span>

                    ${
                        runner3
                        ? `
                            <span>
                                vs
                            </span>

                            <span>
                                ${runner3}
                            </span>
                        `
                        : ""
                    }

                    ${
                        dateText
                        ? `
                            <span>
                                • ${escapeHtml(dateText)}
                            </span>
                        `
                        : ""
                    }

                </div>

            </div>


            <div
                class="odds-cell back-cell"
                data-action="open-match"
            >
                <div class="odds-pair">

                    <span class="odds-value">
                        View
                    </span>

                    <span class="odds-volume">
                        market
                    </span>

                </div>
            </div>


            <div
                class="odds-cell lay-cell"
                data-action="open-match"
            >
                <div class="odds-pair">

                    <span class="odds-value">
                        View
                    </span>

                    <span class="odds-volume">
                        market
                    </span>

                </div>
            </div>


            <div
                class="odds-cell draw-cell"
                data-action="open-match"
            >
                <div class="odds-pair">

                    <span class="odds-value">
                        -
                    </span>

                </div>
            </div>


            <div
                class="odds-cell"
                style="
                    background:#f5f7f8;
                    color:#1976d2;
                "
                data-action="open-match"
            >
                <div class="odds-pair">

                    <span class="odds-value">
                        Open
                    </span>

                    <span class="odds-volume">
                        ProExch
                    </span>

                </div>
            </div>

        </div>
    `;
}


/*
|--------------------------------------------------------------------------
| MATCH EVENTS
|--------------------------------------------------------------------------
*/

function attachMatchEvents() {

    document
        .querySelectorAll("[data-match-url]")
        .forEach(element => {

            element.addEventListener(
                "click",
                function () {

                    const url =
                        this.dataset.matchUrl;

                    if (url) {
                        window.location.href = url;
                    }
                }
            );
        });


    document
        .querySelectorAll('[data-action="open-match"]')
        .forEach(element => {

            element.addEventListener(
                "click",
                function () {

                    const row =
                        this.closest(".match-row");

                    if (!row) {
                        return;
                    }

                    const gameId =
                        row.dataset.gameId;

                    if (!gameId) {
                        return;
                    }

                    window.location.href =
                        `/match/${encodeURIComponent(gameId)}`;
                }
            );
        });
}


/*
|--------------------------------------------------------------------------
| FORMAT DATE
|--------------------------------------------------------------------------
*/

function formatDate(value) {

    if (!value) {
        return "";
    }

    let date;

    try {

        /*
         * ProExch may return ISO-style dates.
         */

        date = new Date(value);

        if (Number.isNaN(date.getTime())) {
            return String(value);
        }

    } catch (error) {

        return String(value);
    }

    return date.toLocaleString(
        undefined,
        {
            day: "2-digit",
            month: "short",
            hour: "2-digit",
            minute: "2-digit"
        }
    );
}


/*
|--------------------------------------------------------------------------
| ESCAPE HTML
|--------------------------------------------------------------------------
*/

function escapeHtml(value) {

    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


/*
|--------------------------------------------------------------------------
| SET FILTER
|--------------------------------------------------------------------------
*/

function setFilter(filter) {

    currentFilter = filter;

    document
        .querySelectorAll("[data-filter]")
        .forEach(button => {

            button.classList.toggle(
                "active",
                button.dataset.filter === filter
            );
        });

    renderMatches();
}


/*
|--------------------------------------------------------------------------
| FILTER EVENTS
|--------------------------------------------------------------------------
*/

function setupFilters() {

    document
        .querySelectorAll("[data-filter]")
        .forEach(button => {

            button.addEventListener(
                "click",
                function () {

                    setFilter(
                        this.dataset.filter
                    );
                }
            );
        });
}


/*
|--------------------------------------------------------------------------
| REFRESH BUTTON
|--------------------------------------------------------------------------
*/

function setupRefreshButton() {

    const button =
        byId("refreshButton");

    if (!button) {
        return;
    }

    button.addEventListener(
        "click",
        async function () {

            button.disabled = true;

            const originalText =
                button.textContent;

            button.textContent =
                "Refreshing...";

            await loadMatches(false);

            button.disabled = false;

            button.textContent =
                originalText;
        }
    );
}


/*
|--------------------------------------------------------------------------
| AUTO REFRESH
|--------------------------------------------------------------------------
*/

function startAutoRefresh() {

    if (refreshTimer) {
        clearInterval(refreshTimer);
    }

    refreshTimer = setInterval(
        function () {

            loadMatches(false);

        },
        REFRESH_INTERVAL
    );
}


/*
|--------------------------------------------------------------------------
| INITIALIZE
|--------------------------------------------------------------------------
*/

document.addEventListener(
    "DOMContentLoaded",
    function () {

        setupFilters();

        setupRefreshButton();

        loadMatches(true);

        startAutoRefresh();

    }
);