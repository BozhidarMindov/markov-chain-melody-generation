import random
import uuid
from collections import defaultdict, Counter

from mido import MidiTrack, Message, MidiFile, bpm2tempo, MetaMessage


class MarkovChain:
    """
    An N-order Markov chain for sequences of MIDI note tuples.

    Attributes:
        order (int): The N context window size.
        model (defaultdict(Counter)): Maps each N-tuple context to a Counter of successor events.
    """
    def __init__(self, order):
        """
        Initialize a new MarkovChain.

        Args:
           order (int): The number of past events to take account for.
        """
        self.order = order
        self.model = defaultdict(Counter)

    def train(self, sequence):
        """
        Build the transition counts from a sequence of note tuples.

        Each element of `sequence` should be a tuple:
            ((note_on_pitch, note_on_velocity, note_on_time), (note_off_pitch, note_off_velocity, note_off_time))

        Raises:
            ValueError: If `sequence` length <= order.
        """
        if len(sequence) <= self.order:
            raise ValueError(f"Cannot train MarkovChain(order={self.order}) on sequence of length={len(sequence)}.")

        sequence_length = len(sequence)
        # Count every N-window -> successor transition
        for i in range(sequence_length - self.order):
            current_state = tuple(sequence[i:i + self.order])
            next_state = sequence[i + self.order]
            self.model[current_state][next_state] += 1

        # Append the tail if it is not present in the model
        tail = tuple(sequence[-self.order:])
        self.model.setdefault(tail, Counter())

    def generate(self, length):
        """
        Generate a new sequence of a specified length using the learned model.

        Args:
            length (int): The total number of events to generate.

        Returns:
            List of generated event-tuples, each matching those seen in training.

        Raises:
            ValueError: If the model is empty or if length <= order.
        """
        if not self.model:
            raise ValueError("The Markov model is empty. Train it first.")
        if length <= self.order:
            raise ValueError(f"Cannot generate {length} notes with order={self.order}.")

        states = list(self.model.keys())

        # Pick the initial state at random
        current_state = random.choice(states)
        result = list(current_state)

        for _ in range(length - self.order):
            next_notes = self.model.get(current_state)
            if next_notes:
                choices, counts = zip(*next_notes.items())
                total = sum(counts)
                # Normalize to probabilities
                probabilities = [c / total for c in counts]
                next_note = random.choices(choices, weights=probabilities, k=1)[0]
            else:
                # Dead‐end -> pick a random state, then one of its notes
                current_state = random.choice(states)
                next_note = random.choice(current_state)

            result.append(next_note)
            current_state = tuple(result[-self.order:])

        return result


def extract_notes(midi_file_path, default_off_time=480):
    """
    Read a MIDI file and extract note-on/note-off pairs.

    Args:
        midi_file_path (str): The path to the MIDI file.
        default_off_time (int): The fallback time if no off-event is found.

    Returns:
        List of tuples: [((on_pitch, on_velocity, on_time),
                          (off_pitch, off_velocity, off_time)), ...]
    """
    mid = MidiFile(midi_file_path)
    pairs = []

    for track in mid.tracks:
        for i, msg in enumerate(track):
            if msg.type == "note_on" and msg.velocity > 0:
                # Capture the on message fields
                on = (msg.note, msg.velocity, msg.time)

                # Look ahead for the first matching off note
                off = None
                for msg2 in track[i + 1:]:
                    if (msg2.type == "note_off" or (msg2.type == "note_on" and msg2.velocity == 0)) and msg2.note == msg.note:
                        off = (msg2.note, msg2.velocity, msg2.time)
                        break

                if off is None:
                    # No matching off note -> give it a default gap
                    off = (msg.note, 0, default_off_time)

                pairs.append((on, off))

    return pairs


def save_melody(pairs, original_midi, output_path):
    """
    Write a sequence of note tuples back into a new MIDI file.

    Args:
        pairs (list): A list of note tuples.
        original_midi (MidiFile): The original MidiFile to copy timing info from.
        output_path (str): The place to save the new MIDI file.
    """
    # Create a new MidiFile and get ticks_per_beat from the original file
    mid_out = MidiFile()
    mid_out.ticks_per_beat = original_midi.ticks_per_beat

    # Build the track
    track = MidiTrack()
    mid_out.tracks.append(track)

    # Copy the tempo from the original (or fall back to 120 BPM if no tempo is found)
    for msg in original_midi.tracks[0]:
        if msg.type == "set_tempo":
            track.append(msg.copy(time=0))
            print(f"Setting tempo: {msg}")
            break
    else:
        # If tempo found -> default to 120 BPM
        track.append(MetaMessage("set_tempo",
                                 tempo=bpm2tempo(120),
                                 time=0))
        print("No tempo found, using default 120 BPM")

    # Replay the note_on/note_off pairs exactly as they were recorded
    for (note, vel_on, delta_on), (_, vel_off, delta_off) in pairs:
        track.append(Message("note_on",
                             note=note,
                             velocity=vel_on,
                             time=delta_on))
        track.append(Message("note_off",
                             note=note,
                             velocity=vel_off,
                             time=delta_off))

    # Save the file
    mid_out.save(output_path)


def main():
    input_midi = "Martin Garrix - Animals.mid"
    generated_notes_length = 100
    chain_order = 2

    original = MidiFile(input_midi)
    output_midi = f"generated_song_{uuid.uuid4()}.mid"

    print("Extracting notes...")
    training_notes = extract_notes(input_midi)
    print(f"Extracted {len(training_notes)} notes.")

    print(f"Training Markov Chain (order={chain_order})...")
    mc = MarkovChain(order=chain_order)
    mc.train(training_notes)

    print(f"Generating new melody with {generated_notes_length} notes...")
    generated_notes = mc.generate(length=generated_notes_length)

    print("Saving new melody to MIDI...")
    save_melody(generated_notes, original, output_midi)
    print(f"New song saved as '{output_midi}'")


if __name__ == "__main__":
    main()
