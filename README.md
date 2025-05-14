# MIDI Melody Generation with Markov Chains

A simple Python tool that reads a MIDI file, learns an N-th order Markov chain over full note-on/note-off events (including pitch, velocity, and timing), and generates new melodies in the same style.

---

## Features

- **Higher-order model**  
  Learns transitions over windows of _N_ consecutive note events to capture short melodic context.

- **Full event tuples**  
  Each state is a pair `(note_on, note_off)` tuple containing `(pitch, velocity, time)`.

- **Dead-end handling**  
  If the chain ever reaches a context with no outgoing transitions, it randomly re-seeds.

- **Tempo & timing preservation**  
  Copies the original file’s tempo and ticks-per-beat to the generated output.

---

## Requirements

- Python 3.7+  
- [mido](https://pypi.org/project/mido/)  

---

## License
This project is released under the MIT License. Feel free to adapt and extend it!

## Acknowledgments
This project was created as my final project for the Theory of Automata course at the American University in Bulgaria.

**Professor**: Soowhan Yoon 
