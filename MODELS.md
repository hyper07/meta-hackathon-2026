# Models

## The question: can we train without labels, using JEPA?

- **What JEPA is.** JEPA (Joint Embedding Predictive Architecture) is Meta's self-supervised approach. The model hides part of its input and learns to predict that part's representation, not the raw pixels or words. It needs no labels.
- **What is released.** The open release is **V-JEPA 2**, a video model for physical-world prediction and robot planning. Code and weights are public under **CC-BY-NC**, which is non-commercial ([overview](https://xpert.digital/en/the-ai-​​model-v-jepa-2-from-meta/?amp=1), [listing](https://peerpush.com/p/v-jepa-2)). As of 2026-10-18 no text JEPA has been released that we found.
- **Why it doesn't fit here:**
  - It reads video, not text.
  - The non-commercial licence rules out the Startup track.
  - Learning without labels gives a model that represents language, but not one that knows which conversations are harassment. That still needs a model that already understands language, or labelled examples.
- **Our own integer byte LM (SemanticCommunication)** predicts bytes for compression and has no notion of meaning. It is not useful as a detector.

**What "without labels" can mean in practice:**

1. **Zero-shot.** Start from a model that already understands language (Llama, Muse Spark through the Meta Model API) and describe the categories in the prompt. No training.
2. **Self-supervised plus a little labelling.** Embed messages with an open encoder and train a small classifier on a few hundred labelled examples. Or let the large model label data, then have people check a sample.
3. **Fine-tune.** Fine-tune a small open model, a Llama 3.x 1B to 8B class model, with LoRA on a labelled set. This is the path to an on-device detector.

## Proposed stack

| Job | Model | Why |
|---|---|---|
| Is this conversation unsafe? (first pass) | Llama Guard (Meta, open weights) with our own category list | built for safety classification; you can define custom categories |
| Why, which lines, which category | Llama (open weights) or Muse Spark (Meta Model API) with a structured-output prompt | quotes the exact lines, so the flag can be checked |
| Assessment agent | the same large model, with tools: timeline, report draft, retrieval | conversational, trauma-informed prompt |
| Safety mode: discard, ask or alert | Muse Spark 1.1 (Meta Model API); later a small Llama fine-tuned on its labels | a probability for each option in about 2 s; rules, not the model, pick the action; see [DESIGN.md](DESIGN.md) §6 |
| Legal information | retrieval over public statutes and Title IX documents, plus the large model, answers with citations | grounded answers, not invented law |
| On device (stretch) | a small Llama fine-tuned with LoRA on labelled data, quantized | raw messages never leave the phone |
| Voice notes and calls (stretch) | speech-to-text, then the same detector | the user's own recordings only |

## Data

- **Public datasets** for harassment, toxicity and hate speech, from academic and Kaggle sources. Check each dataset's licence.
  - They are mostly social-media comments, not private conversations about an assault, so expect a domain gap.
  - Synthetic conversations written with advocates' guidance can fill the gap. Label them as synthetic, and never use real victims' messages without consent.
- **Hard cases to include:**
  - jokes and banter;
  - consensual flirting;
  - people describing someone else's experience;
  - news discussion;
  - coded language;
  - several languages.

## Evaluation (the judges will ask)

- Recall on the "urgent" class. Missing a real emergency is the worst failure.
- False-positive rate on normal conversations. Too many alerts and people turn it off.
- Per-category precision and recall, against a small human-labelled test set kept separate from all prompts and training.
- Time to flag a conversation, on the phone and on the server.
- Report all of these with the test set size, n, as for every result in SemanticCommunication.
