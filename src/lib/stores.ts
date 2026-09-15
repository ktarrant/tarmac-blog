import { atom } from "nanostores";

/** The state (two-letter abbreviation) currently hovered or selected, shared across chart islands on a page. */
export const hoveredState = atom<string | null>(null);
