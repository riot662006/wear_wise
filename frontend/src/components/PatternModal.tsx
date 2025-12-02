import Modal from "./Modal";
import PatternSection, { type PatternItem } from "./PatternSection";

export default function PatternModal({
  open,
  items,
  onClose,
}: {
  open: boolean;
  items: PatternItem[];
  onClose: () => void;
}) {
  return (
    <Modal open={open} title="Pattern Analysis" onClose={onClose}>
      <PatternSection items={items} />
    </Modal>
  );
}
