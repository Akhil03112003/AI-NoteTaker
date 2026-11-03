import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, expect, it } from "vitest";
import { Transcript } from "./Transcript";

let container: HTMLDivElement | undefined;
let root: Root | undefined;

afterEach(() => {
  if (root) act(() => root?.unmount());
  container?.remove();
  root = undefined;
  container = undefined;
});

it("renders Deepgram speaker labels and leaves missing IDs unattributed", () => {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);

  act(() => {
    root?.render(
      <Transcript
        isProcessing={false}
        segments={[
          { id: "one", ordinal: 0, text: "First voice", speaker_label: "Speaker 0", start_ms: 0, end_ms: 500 },
          { id: "two", ordinal: 1, text: "Second voice", speaker_label: "Speaker 1", start_ms: 500, end_ms: 1000 },
          { id: "unknown", ordinal: 2, text: "Unattributed voice", speaker_label: null, start_ms: 1000, end_ms: 1500 },
        ]}
      />,
    );
  });

  expect(container.textContent).toContain("Speaker 0");
  expect(container.textContent).toContain("Speaker 1");
  expect(container.textContent).not.toContain("Speaker 2");
  expect(container.textContent).toContain("Unattributed voice");
});
