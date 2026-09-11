
"use strict";

/* =========================================================
   CRICBET DASHBOARD
   PROEXCH MATCH + ODDS
========================================================= */

let allMatches = [];
let currentFilter = "all";

const oddsCache = new Map();
const oddsLoading = new Set();

const WHATSAPP_NUMBER = "918895898319";

const MATCH_REFRESH_MS = 30000;
const ODDS_REFRESH_MS = 5000;


/* =========================================================
   HTML ESCAPE
========================================================= */

function escapeHtml(value) {

    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


/* =========================================================
   NUMBER
========================================================= */

function toNumber(value) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return null;
    }

    const n = Number(value);

    return Number.isFinite(n) ? n : null;
}


/* =========================================================
   LIVE CHECK
========================================================= */

function isLive(match) {

    if (!match) {
        return false;
    }

    const value =
        match.in_play ??
        match.inPlay;

    return (
        value === true ||
        value === 1 ||
        value === "1" ||
        value === "true" ||
        value === "True"
    );
}


/* =========================================================
   DATE
========================================================= */

function formatDate(value) {

    if (!value) {
        return "";
    }

    try {

        const date = new Date(value);

        if (Number.isNaN(date.getTime())) {
            return String(value);
        }

        return date.toLocaleString(
            "en-IN",
            {
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit"
            }
        );

    } catch {

        return String(value);

    }
}


/* =========================================================
   WHATSAPP
========================================================= */

function openWhatsApp(message) {

    if (!WHATSAPP_NUMBER) {
        console.error(
            "WhatsApp number is not configured."
        );
        return;
    }

    const url =
        `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(message)}`;

    window.open(
        url,
        "_blank",
        "noopener,noreferrer"
    );
}


function openDepositWhatsApp() {

    openWhatsApp(
        "Hello, I want to make a deposit in CricBet."
    );
}


function openWithdrawWhatsApp() {

    openWhatsApp(
        "Hello, I want to make a withdrawal from CricBet."
    );
}


/* =========================================================
   GET GAME ID
========================================================= */

function getGameId(match) {

    return String(
        match?.game_id ??
        match?.gameId ??
        ""
    ).trim();
}


/* =========================================================
   GET MARKET ID
========================================================= */

function getMarketId(match) {

    return String(
        match?.market_id ??
        match?.marketId ??
        ""
    ).trim();
}


/* =========================================================
   ODDS ROOT
========================================================= */

function getOddsRoot(payload) {

    if (!payload) {
        return null;
    }

    /*
     * Your router may return:
     *
     * {
     *   success: true,
     *   odds: {...}
     * }
     */

    if (
        payload.odds &&
        typeof payload.odds === "object"
    ) {
        return payload.odds;
    }


    /*
     * Or:
     *
     * {
     *   success: true,
     *   data: {...}
     * }
     */

    if (
        payload.data &&
        typeof payload.data === "object"
    ) {

        if (
            payload.data.data &&
            typeof payload.data.data === "object"
        ) {
            return payload.data.data;
        }

        return payload.data;
    }


    return payload;
}


/* =========================================================
   FIND MATCH ODDS
========================================================= */

function findMatchOdds(payload) {

    const root =
        getOddsRoot(payload);

    if (!root) {
        return null;
    }


    /*
     * Direct:
     *
     * matchOdds: [...]
     */

    if (
        Array.isArray(root.matchOdds)
    ) {
        return root.matchOdds;
    }


    /*
     * Lowercase variation.
     */

    if (
        Array.isArray(root.match_odds)
    ) {
        return root.match_odds;
    }


    /*
     * Uppercase variation.
     */

    if (
        Array.isArray(root.MATCH_ODDS)
    ) {
        return root.MATCH_ODDS;
    }


    /*
     * Sometimes data is nested.
     */

    if (
        root.matchOdds &&
        typeof root.matchOdds === "object"
    ) {
        return root.matchOdds;
    }


    if (
        root.MATCH_ODDS &&
        typeof root.MATCH_ODDS === "object"
    ) {
        return root.MATCH_ODDS;
    }


    /*
     * Search recursively for matchOdds.
     */

    if (
        typeof root === "object"
    ) {

        for (
            const key of Object.keys(root)
        ) {

            const value =
                root[key];

            if (
                key.toLowerCase() ===
                "matchodds"
            ) {
                return value;
            }

        }

    }


    return null;
}


/* =========================================================
   FIND RUNNERS
========================================================= */

function findRunners(value) {

    if (!value) {
        return [];
    }


    /*
     * Already a runner array.
     */

    if (Array.isArray(value)) {

        /*
         * Check whether this itself is a runner list.
         */

        const looksLikeRunners =
            value.some(
                item =>
                    item &&
                    typeof item === "object" &&
                    (
                        item.selectionId !== undefined ||
                        item.selection_id !== undefined ||
                        item.sid !== undefined ||
                        item.runnerName !== undefined ||
                        item.runner_name !== undefined ||
                        item.back !== undefined ||
                        item.lay !== undefined
                    )
            );


        if (looksLikeRunners) {
            return value;
        }


        /*
         * Otherwise search each object.
         */

        for (
            const item of value
        ) {

            const result =
                findRunners(item);

            if (result.length) {
                return result;
            }

        }

        return [];
    }


    if (
        typeof value !== "object"
    ) {
        return [];
    }


    /*
     * Common runner property names.
     */

    const possibleKeys = [
        "runners",
        "runner",
        "selections",
        "selection",
        "oddDatas",
        "odds",
        "data"
    ];


    for (
        const key of possibleKeys
    ) {

        if (
            value[key] !== undefined
        ) {

            const result =
                findRunners(
                    value[key]
                );

            if (result.length) {
                return result;
            }

        }

    }


    /*
     * Recursive fallback.
     */

    for (
        const key of Object.keys(value)
    ) {

        const child =
            value[key];

        if (
            child &&
            typeof child === "object"
        ) {

            const result =
                findRunners(child);

            if (result.length) {
                return result;
            }

        }

    }


    return [];
}


/* =========================================================
   SELECTION ID
========================================================= */

function getSelectionId(item) {

    if (!item) {
        return null;
    }

    return (
        item.selectionId ??
        item.selection_id ??
        item.selectionID ??
        item.sid ??
        item.runnerId ??
        item.runner_id ??
        null
    );
}


/* =========================================================
   RUNNER NAME
========================================================= */

function getRunnerName(item) {

    if (!item) {
        return "";
    }

    return (
        item.runnerName ??
        item.runner_name ??
        item.selectionName ??
        item.selection_name ??
        item.name ??
        item.runner ??
        item.teamName ??
        item.team ??
        ""
    );
}


/* =========================================================
   PRICE EXTRACTION
========================================================= */

function extractPrice(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return null;
    }


    if (
        typeof value === "number"
    ) {
        return Number.isFinite(value)
            ? value
            : null;
    }


    if (
        typeof value === "string"
    ) {
        return toNumber(value);
    }


    if (
        typeof value === "object"
    ) {

        return (
            toNumber(value.price) ??
            toNumber(value.odds) ??
            toNumber(value.rate) ??
            toNumber(value.value) ??
            toNumber(value.size)
        );

    }


    return null;
}


/* =========================================================
   BACK PRICE
========================================================= */

function getBackPrice(item) {

    if (!item) {
        return null;
    }


    /*
     * Standard names.
     */

    const candidates = [
        item.back,
        item.Back,
        item.backPrice,
        item.back_price,
        item.backOdds,
        item.back_odds,
        item.backRate,
        item.back_rate,
        item.backOdd,
        item.back_odd,
        item.b1,
        item.batb,
        item.back1
    ];


    for (
        const value of candidates
    ) {

        const price =
            extractPrice(value);

        if (price !== null) {
            return price;
        }

    }


    /*
     * Some APIs return:
     *
     * back: [
     *   {price: 1.50}
     * ]
     */

    if (
        Array.isArray(item.back)
    ) {

        for (
            const entry of item.back
        ) {

            const price =
                extractPrice(entry);

            if (price !== null) {
                return price;
            }

        }

    }


    return null;
}


/* =========================================================
   LAY PRICE
========================================================= */

function getLayPrice(item) {

    if (!item) {
        return null;
    }


    const candidates = [
        item.lay,
        item.Lay,
        item.layPrice,
        item.lay_price,
        item.layOdds,
        item.lay_odds,
        item.layRate,
        item.lay_rate,
        item.layOdd,
        item.lay_odd,
        item.l1,
        item.layb,
        item.lay1
    ];


    for (
        const value of candidates
    ) {

        const price =
            extractPrice(value);

        if (price !== null) {
            return price;
        }

    }


    if (
        Array.isArray(item.lay)
    ) {

        for (
            const entry of item.lay
        ) {

            const price =
                extractPrice(entry);

            if (price !== null) {
                return price;
            }

        }

    }


    return null;
}


/* =========================================================
   NORMALIZE RUNNERS
========================================================= */

function normalizeRunners(runners) {

    if (
        !Array.isArray(runners)
    ) {
        return [];
    }


    return runners
        .map(
            item => {

                if (
                    !item ||
                    typeof item !== "object"
                ) {
                    return null;
                }


                return {
                    selectionId:
                        getSelectionId(item),

                    name:
                        getRunnerName(item),

                    back:
                        getBackPrice(item),

                    lay:
                        getLayPrice(item)
                };

            }
        )
        .filter(Boolean);

}


/* =========================================================
   NORMALIZE MATCH ODDS
========================================================= */

function normalizeMatchOdds(
    match,
    payload
) {

    const matchOdds =
        findMatchOdds(payload);


    if (!matchOdds) {

        console.warn(
            "MATCH ODDS NOT FOUND:",
            getGameId(match),
            payload
        );

        return {
            team1: {
                back: null,
                lay: null
            },

            team2: {
                back: null,
                lay: null
            },

            team3: {
                back: null,
                lay: null
            }
        };

    }


    const runners =
        normalizeRunners(
            findRunners(
                matchOdds
            )
        );


    if (!runners.length) {

        console.warn(
            "NO RUNNERS FOUND:",
            getGameId(match),
            matchOdds
        );

        return {
            team1: {
                back: null,
                lay: null
            },

            team2: {
                back: null,
                lay: null
            },

            team3: {
                back: null,
                lay: null
            }
        };

    }


    console.log(
        "NORMALIZED RUNNERS:",
        getGameId(match),
        runners
    );


    const selectionIds = [

        match.selection_id1 ??
        match.selectionId1,

        match.selection_id2 ??
        match.selectionId2,

        match.selection_id3 ??
        match.selectionId3

    ].map(
        value =>
            value === null ||
            value === undefined
                ? null
                : String(value)
    );


    const slots = [
        "team1",
        "team2",
        "team3"
    ];


    const result = {

        team1: {
            back: null,
            lay: null
        },

        team2: {
            back: null,
            lay: null
        },

        team3: {
            back: null,
            lay: null
        }

    };


    /*
     * First match by selection ID.
     */

    runners.forEach(
        runner => {

            if (
                runner.selectionId === null ||
                runner.selectionId === undefined
            ) {
                return;
            }


            const runnerId =
                String(
                    runner.selectionId
                );


            const index =
                selectionIds.indexOf(
                    runnerId
                );


            if (
                index >= 0
            ) {

                result[
                    slots[index]
                ] = {

                    back:
                        runner.back,

                    lay:
                        runner.lay

                };

            }

        }
    );


    /*
     * If selection IDs aren't present,
     * use runner order.
     */

    runners
        .slice(0, 3)
        .forEach(
            (runner, index) => {

                const slot =
                    slots[index];


                if (
                    result[slot].back === null &&
                    result[slot].lay === null
                ) {

                    result[slot] = {

                        back:
                            runner.back,

                        lay:
                            runner.lay

                    };

                }

            }
        );


    return result;
}


/* =========================================================
   ODDS HTML
========================================================= */

function createOddsButton({
    gameId,
    marketId,
    team,
    side,
    price,
    className
}) {

    const numericPrice =
        toNumber(price);


    const disabled =
        numericPrice === null;


    const displayPrice =
        numericPrice !== null
            ? numericPrice.toFixed(2)
            : "-";


    return `

        <button
            type="button"
            class="odds-cell ${className}"
            data-game-id="${escapeHtml(gameId)}"
            data-market-id="${escapeHtml(marketId)}"
            data-team="${escapeHtml(team)}"
            data-side="${escapeHtml(side)}"
            data-price="${
                numericPrice !== null
                    ? numericPrice
                    : ""
            }"
            ${disabled ? "disabled" : ""}
            title="${escapeHtml(team)} ${escapeHtml(side)}"
        >

            <span class="odds-price">
                ${escapeHtml(displayPrice)}
            </span>

        </button>

    `;
}


/* =========================================================
   CREATE MATCH ROW
========================================================= */

function createMatchRow(match) {

    const gameId =
        getGameId(match);


    const marketId =
        getMarketId(match);


    const eventName =
        match.event_name ??
        match.eventName ??
        "Cricket Match";


    const eventTime =
        match.event_time ??
        match.eventTime ??
        "";


    const team1 =
        match.team1 ??
        match.runnerName1 ??
        "Team 1";


    const team2 =
        match.team2 ??
        match.runnerName2 ??
        "Team 2";


    const team3 =
        match.team3 ??
        match.runnerName3 ??
        "The Draw";


    const live =
        isLive(match);


    /*
     * Get cached odds.
     */

    let odds = {

        team1: {
            back: null,
            lay: null
        },

        team2: {
            back: null,
            lay: null
        },

        team3: {
            back: null,
            lay: null
        }

    };


    if (
        oddsCache.has(gameId)
    ) {

        odds =
            normalizeMatchOdds(
                match,
                oddsCache.get(gameId)
            );

    }


    return `

        <div
            class="sportsbook-match-row"
            data-game-id="${escapeHtml(gameId)}"
            data-market-id="${escapeHtml(marketId)}"
        >

            <!-- MATCH INFORMATION -->

            <div class="match-information">

                <div class="match-status-line">

                    ${
                        live
                            ? `
                                <span class="live-dot"></span>

                                <span class="match-status live-status">
                                    LIVE
                                </span>
                              `
                            : `
                                <span class="match-status upcoming-status">
                                    UPCOMING
                                </span>
                              `
                    }

                    <span class="match-time">
                        ${escapeHtml(
                            formatDate(eventTime)
                        )}
                    </span>

                </div>


                <div class="match-name">
                    ${escapeHtml(eventName)}
                </div>


                <div class="team-names">

                    <div class="team-name">
                        ${escapeHtml(team1)}
                    </div>

                    <div class="team-name">
                        ${escapeHtml(team2)}
                    </div>

                    ${
                        team3 &&
                        team3 !== "The Draw"
                            ? `
                                <div class="team-name">
                                    ${escapeHtml(team3)}
                                </div>
                              `
                            : ""
                    }

                </div>


                <div class="match-league">
                    Cricket
                </div>

            </div>


            <!-- TEAM 1 BACK -->

            ${createOddsButton({

                gameId,
                marketId,

                team:
                    team1,

                side:
                    "back",

                price:
                    odds.team1.back,

                className:
                    "odds-team-1"

            })}


            <!-- TEAM 2 BACK -->

            ${createOddsButton({

                gameId,
                marketId,

                team:
                    team2,

                side:
                    "back",

                price:
                    odds.team2.back,

                className:
                    "odds-team-2"

            })}


            <!-- DRAW BACK -->

            ${createOddsButton({

                gameId,
                marketId,

                team:
                    team3,

                side:
                    "back",

                price:
                    odds.team3.back,

                className:
                    "odds-draw"

            })}


            <!-- VIEW MATCH -->

            <div class="match-action">

                <a
                    class="view-match-button"
                    href="/match/${encodeURIComponent(gameId)}"
                >
                    <span>→</span>
                    VIEW MATCH
                </a>

            </div>

        </div>

    `;
}


/* =========================================================
   LOAD MATCHES
========================================================= */

async function loadMatches() {

    const container =
        document.getElementById(
            "matches"
        );


    if (!container) {
        return;
    }


    /*
     * Only show loading on first request.
     */

    if (!allMatches.length) {

        container.innerHTML = `

            <div class="empty-state">

                <div class="empty-state-icon">
                    🏏
                </div>

                <div class="empty-state-title">
                    Loading cricket matches...
                </div>

                <div class="empty-state-text">
                    Fetching live cricket data.
                </div>

            </div>

        `;

    }


    try {

        const response =
            await fetch(
                "/api/cricket/matches",
                {
                    method: "GET",
                    credentials: "same-origin",
                    cache: "no-store",
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );


        let payload;


        try {

            payload =
                await response.json();

        } catch {

            throw new Error(
                "Server returned invalid JSON."
            );

        }


        if (!response.ok) {

            throw new Error(
                payload?.error ||
                payload?.detail ||
                "Unable to load cricket matches."
            );

        }


        if (
            payload.success !== true
        ) {

            throw new Error(
                payload?.error ||
                "Cricket API request failed."
            );

        }


        if (
            !Array.isArray(
                payload.matches
            )
        ) {

            throw new Error(
                "Invalid matches response."
            );

        }


        allMatches =
            payload.matches;


        console.log(
            "CRICBET MATCHES:",
            allMatches.length
        );


        renderMatches();


        /*
         * Odds are loaded separately.
         */

        loadAllOdds();


    } catch (error) {

        console.error(
            "CRICKET MATCH ERROR:",
            error
        );


        if (!allMatches.length) {

            container.innerHTML = `

                <div class="empty-state">

                    <div class="empty-state-icon">
                        ⚠️
                    </div>

                    <div class="empty-state-title">
                        Unable to load cricket data
                    </div>

                    <div class="empty-state-text">
                        ${escapeHtml(
                            error.message
                        )}
                    </div>

                    <button
                        type="button"
                        class="retry-matches-button"
                        onclick="loadMatches()"
                    >
                        RETRY
                    </button>

                </div>

            `;

        }

    }

}


/* =========================================================
   LOAD ODDS FOR ONE MATCH
========================================================= */

async function loadOddsForMatch(match) {

    const gameId =
        getGameId(match);


    if (!gameId) {
        return;
    }


    /*
     * Don't request the same match twice
     * at the same time.
     */

    if (
        oddsLoading.has(gameId)
    ) {
        return;
    }


    oddsLoading.add(gameId);


    try {

        console.log(
            "GET ODDS:",
            gameId
        );


        /*
         * IMPORTANT:
         *
         * New ProExch endpoint:
         *
         * /api/cricket/odds?gameId=<gameId>
         */

        const response =
            await fetch(
                `/api/cricket/odds?gameId=${encodeURIComponent(gameId)}`,
                {
                    method: "GET",
                    credentials: "same-origin",
                    cache: "no-store",
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );


        let payload;


        try {

            payload =
                await response.json();

        } catch {

            throw new Error(
                "Invalid odds JSON."
            );

        }


        if (!response.ok) {

            throw new Error(
                payload?.error ||
                payload?.detail ||
                `Odds HTTP ${response.status}`
            );

        }


        if (
            payload.success !== true
        ) {

            throw new Error(
                payload?.error ||
                "Odds request failed."
            );

        }


        /*
         * Store the entire odds object.
         */

        oddsCache.set(
            gameId,
            payload.odds ??
            payload.data ??
            payload
        );


        console.log(
            "ODDS RECEIVED:",
            gameId,
            oddsCache.get(gameId)
        );


        /*
         * Update only this row.
         */

        updateMatchOdds(
            match
        );


    } catch (error) {

        console.warn(
            "ODDS ERROR:",
            gameId,
            error.message
        );

    } finally {

        oddsLoading.delete(
            gameId
        );

    }

}


/* =========================================================
   LOAD ALL ODDS
========================================================= */

async function loadAllOdds() {

    if (!allMatches.length) {
        return;
    }


    /*
     * Small batches prevent 26 requests
     * from hitting the VPS at exactly
     * the same time.
     */

    const batchSize = 5;


    for (
        let i = 0;
        i < allMatches.length;
        i += batchSize
    ) {

        const batch =
            allMatches.slice(
                i,
                i + batchSize
            );


        await Promise.all(
            batch.map(
                match =>
                    loadOddsForMatch(
                        match
                    )
            )
        );

    }

}


/* =========================================================
   UPDATE MATCH ODDS
========================================================= */

function updateMatchOdds(match) {

    const gameId =
        getGameId(match);


    if (!gameId) {
        return;
    }


    const row =
        document.querySelector(
            `.sportsbook-match-row[data-game-id="${CSS.escape(gameId)}"]`
        );


    if (!row) {
        return;
    }


    if (
        !oddsCache.has(gameId)
    ) {
        return;
    }


    const odds =
        normalizeMatchOdds(
            match,
            oddsCache.get(gameId)
        );


    updateOddsButton(
        row.querySelector(
            ".odds-team-1"
        ),
        odds.team1.back
    );


    updateOddsButton(
        row.querySelector(
            ".odds-team-2"
        ),
        odds.team2.back
    );


    updateOddsButton(
        row.querySelector(
            ".odds-draw"
        ),
        odds.team3.back
    );

}


/* =========================================================
   UPDATE ODDS BUTTON
========================================================= */

function updateOddsButton(
    button,
    price
) {

    if (!button) {
        return;
    }


    const numericPrice =
        toNumber(price);


    const span =
        button.querySelector(
            ".odds-price"
        );


    if (
        numericPrice === null
    ) {

        button.disabled = true;

        button.dataset.price = "";

        if (span) {
            span.textContent = "-";
        }

        return;
    }


    button.disabled = false;

    button.dataset.price =
        String(numericPrice);


    if (span) {

        span.textContent =
            numericPrice.toFixed(2);

    }

}


/* =========================================================
   FILTER
========================================================= */

function setFilter(filter) {

    currentFilter =
        filter;


    document
        .querySelectorAll(
            ".sport-filter"
        )
        .forEach(button => {

            button.classList.toggle(
                "active",
                button.dataset.filter === filter
            );

        });


    renderMatches();

}


/* =========================================================
   RENDER MATCHES
========================================================= */

function renderMatches() {

    const container =
        document.getElementById(
            "matches"
        );


    if (!container) {
        return;
    }


    let matches =
        [...allMatches];


    if (
        currentFilter === "live"
    ) {

        matches =
            matches.filter(
                match =>
                    isLive(match)
            );

    }


    if (
        currentFilter === "upcoming"
    ) {

        matches =
            matches.filter(
                match =>
                    !isLive(match)
            );

    }


    if (!matches.length) {

        container.innerHTML = `

            <div class="empty-state">

                <div class="empty-state-icon">
                    🏏
                </div>

                <div class="empty-state-title">
                    No cricket matches
                </div>

                <div class="empty-state-text">
                    No matches are currently available for this filter.
                </div>

            </div>

        `;

        return;

    }


    container.innerHTML =
        matches
            .map(
                match =>
                    createMatchRow(match)
            )
            .join("");


    /*
     * Apply cached odds immediately.
     */

    matches.forEach(
        match =>
            updateMatchOdds(
                match
            )
    );

}


/* =========================================================
   BALANCE
========================================================= */

async function loadBalance() {

    try {

        const response =
            await fetch(
                "/api/user/balance",
                {
                    method: "GET",
                    credentials: "same-origin",
                    cache: "no-store",
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );


        if (!response.ok) {
            return;
        }


        const data =
            await response.json();


        if (
            data.balance === undefined
        ) {
            return;
        }


        const balance =
            Number(
                data.balance
            );


        const formatted =
            Number.isFinite(balance)
                ? balance.toLocaleString(
                    "en-IN",
                    {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    }
                )
                : "0.00";


        const balanceElement =
            document.getElementById(
                "balance"
            );


        const betslipBalance =
            document.getElementById(
                "betslipBalance"
            );


        if (balanceElement) {

            balanceElement.textContent =
                `₹${formatted}`;

        }


        if (betslipBalance) {

            betslipBalance.textContent =
                `₹${formatted}`;

        }

    } catch (error) {

        console.warn(
            "Balance loading failed:",
            error
        );

    }

}


/* =========================================================
   BETSLIP
========================================================= */

function setupBetslip() {

    const betslip =
        document.getElementById(
            "betslip"
        );


    const closeButton =
        document.getElementById(
            "betslipClose"
        );


    const mobileButton =
        document.getElementById(
            "mobileBetslipButton"
        );


    if (
        closeButton &&
        betslip
    ) {

        closeButton.addEventListener(
            "click",
            () => {

                betslip.classList.remove(
                    "open"
                );

            }
        );

    }


    if (
        mobileButton &&
        betslip
    ) {

        mobileButton.addEventListener(
            "click",
            () => {

                betslip.classList.toggle(
                    "open"
                );

            }
        );

    }

}


/* =========================================================
   ODDS CLICK
========================================================= */

document.addEventListener(
    "click",
    event => {

        const button =
            event.target.closest(
                ".odds-cell"
            );


        if (!button) {
            return;
        }


        if (button.disabled) {
            return;
        }


        const price =
            Number(
                button.dataset.price
            );


        if (!Number.isFinite(price)) {
            return;
        }


        const selection = {

            gameId:
                button.dataset.gameId,

            marketId:
                button.dataset.marketId,

            team:
                button.dataset.team,

            side:
                button.dataset.side,

            price:
                price

        };


        console.log(
            "CRICBET ODDS SELECTED:",
            selection
        );


        /*
         * Existing betslip/place-bet code
         * can listen for this event.
         */

        document.dispatchEvent(
            new CustomEvent(
                "cricbet:oddsSelected",
                {
                    detail:
                        selection
                }
            )
        );

    }
);


/* =========================================================
   INITIALIZE
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        /* -------------------------------------------------
           FILTERS
        ------------------------------------------------- */

        document
            .querySelectorAll(
                ".sport-filter"
            )
            .forEach(button => {

                button.addEventListener(
                    "click",
                    () => {

                        setFilter(
                            button.dataset.filter
                        );

                    }
                );

            });


        /* -------------------------------------------------
           DEPOSIT
        ------------------------------------------------- */

        const depositButton =
            document.getElementById(
                "depositBtn"
            );


        if (depositButton) {

            depositButton.addEventListener(
                "click",
                openDepositWhatsApp
            );

        }


        /* -------------------------------------------------
           WITHDRAW
        ------------------------------------------------- */

        const withdrawButton =
            document.getElementById(
                "withdrawBtn"
            );


        if (withdrawButton) {

            withdrawButton.addEventListener(
                "click",
                openWithdrawWhatsApp
            );

        }


        /* -------------------------------------------------
           BETSLIP
        ------------------------------------------------- */

        setupBetslip();


        /* -------------------------------------------------
           BALANCE
        ------------------------------------------------- */

        loadBalance();


        /* -------------------------------------------------
           MATCHES
        ------------------------------------------------- */

        loadMatches();


        /* -------------------------------------------------
           MATCH REFRESH
        ------------------------------------------------- */

        setInterval(
            loadMatches,
            MATCH_REFRESH_MS
        );


        /* -------------------------------------------------
           ODDS REFRESH
        ------------------------------------------------- */

        setInterval(
            () => {

                if (!allMatches.length) {
                    return;
                }


                /*
                 * Clear the loading state only for
                 * completed requests. The Set itself
                 * prevents duplicate requests.
                 */

                allMatches.forEach(
                    match => {

                        loadOddsForMatch(
                            match
                        );

                    }
                );

            },
            ODDS_REFRESH_MS
        );


        /* -------------------------------------------------
           BALANCE REFRESH
        ------------------------------------------------- */

        setInterval(
            loadBalance,
            15000
        );

    }
);

