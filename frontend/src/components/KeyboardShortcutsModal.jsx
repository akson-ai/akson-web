function KeyboardShortcutsModal() {
  return (
    <dialog id="shortcuts_modal" className="modal">
      <div className="modal-box">
        <h3 className="font-bold text-lg">Keyboard Shortcuts</h3>
        <div className="py-4">
          <table className="table table-zebra">
            <thead>
              <tr>
                <th>Shortcut</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><kbd className="kbd kbd-sm">Cmd</kbd> + <kbd className="kbd kbd-sm">Shift</kbd> + <kbd className="kbd kbd-sm">S</kbd></td>
                <td>Toggle sidebar</td>
              </tr>
              <tr>
                <td><kbd className="kbd kbd-sm">Esc</kbd></td>
                <td>Close sidebar / Cancel current request</td>
              </tr>
              <tr>
                <td><kbd className="kbd kbd-sm">Cmd</kbd> + <kbd className="kbd kbd-sm">Shift</kbd> + <kbd className="kbd kbd-sm">O</kbd></td>
                <td>New chat</td>
              </tr>
              <tr>
                <td><kbd className="kbd kbd-sm">Shift</kbd> + <kbd className="kbd kbd-sm">Esc</kbd></td>
                <td>Focus input</td>
              </tr>
              <tr>
                <td><kbd className="kbd kbd-sm">Cmd</kbd> + <kbd className="kbd kbd-sm">/</kbd></td>
                <td>Show this help</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="modal-action">
          <form method="dialog">
            <button className="btn">Close</button>
          </form>
        </div>
      </div>
    </dialog>
  );
}

export default KeyboardShortcutsModal;
