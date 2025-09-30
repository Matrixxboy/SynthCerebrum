* Electron → desktop shell (builds into `.exe`)
* React → component-based UI (buttons, forms, tables, etc.)
* Tailwind/Bootstrap/Material UI → styling
* Backend logic → Node.js inside Electron

---

## 🔹 Project Structure (Electron + React)

```
my-electron-app/
├── package.json
├── main.js              # Electron entry point
├── public/
│   └── index.html       # React HTML template
└── src/
    ├── App.jsx          # Root React component
    ├── components/
    │   ├── Button.jsx
    │   ├── Form.jsx
    │   └── Table.jsx
    └── index.jsx        # React entry point
```

---

## 🔹 Step 1: Initialize Project

```bash
mkdir my-electron-app
cd my-electron-app
npm init -y
npm install electron react react-dom vite
```

We’ll use **Vite** (fast React bundler).

---

## 🔹 Step 2: Setup Vite + React

```bash
npm create vite@latest
```

* Choose **React** (JS or TS, your choice).
* This creates a `vite` project with `src/` and `index.html`.

Now merge that with your Electron folder.

---

## 🔹 Step 3: Create `main.js` (Electron Entry)

```javascript
const { app, BrowserWindow } = require('electron')
const path = require('path')

function createWindow() {
  const win = new BrowserWindow({
    width: 1000,
    height: 700,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js')
    }
  })

  // In dev: load Vite server
  win.loadURL('http://localhost:5173')

  // In build: load bundled index.html
  // win.loadFile('dist/index.html')
}

app.whenReady().then(createWindow)
```

---

## 🔹 Step 4: React Components Example

**App.jsx**

```jsx
import React from "react"
import Button from "./components/Button"
import Form from "./components/Form"
import Table from "./components/Table"

export default function App() {
  return (
    <div className="p-6 text-center">
      <h1 className="text-2xl font-bold">My Electron + React App</h1>
      <Form />
      <Button />
      <Table />
    </div>
  )
}
```

**Button.jsx**

```jsx
import React from "react"

export default function Button() {
  return (
    <button className="bg-blue-500 text-white px-4 py-2 rounded mt-4">
      Click Me
    </button>
  )
}
```

**Form.jsx**

```jsx
import React, { useState } from "react"

export default function Form() {
  const [name, setName] = useState("")

  return (
    <div className="mt-4">
      <input
        className="border px-2 py-1"
        type="text"
        placeholder="Enter name"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <p className="mt-2">Hello, {name || "Guest"} 👋</p>
    </div>
  )
}
```

**Table.jsx**

```jsx
import React from "react"

export default function Table() {
  const data = [
    { id: 1, name: "Alice", age: 22 },
    { id: 2, name: "Bob", age: 25 },
    { id: 3, name: "Charlie", age: 30 },
  ]

  return (
    <table className="mt-6 border w-full">
      <thead>
        <tr className="bg-gray-200">
          <th className="border px-2">ID</th>
          <th className="border px-2">Name</th>
          <th className="border px-2">Age</th>
        </tr>
      </thead>
      <tbody>
        {data.map((row) => (
          <tr key={row.id}>
            <td className="border px-2">{row.id}</td>
            <td className="border px-2">{row.name}</td>
            <td className="border px-2">{row.age}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
```

---

## 🔹 Step 5: Run Dev Mode

1. Start React:

   ```bash
   npm run dev
   ```
2. Start Electron:

   ```bash
   npx electron .
   ```

👉 Now your **Electron window shows React UI with components**.

---

## 🔹 Step 6: Build for Production

1. Build React:

   ```bash
   npm run build
   ```

   (outputs to `dist/`)

2. Update `main.js` to load:

   ```js
   win.loadFile('dist/index.html')
   ```

3. Package into `.exe`:

   ```bash
   npm install electron-packager -g
   electron-packager . MyApp --platform=win32 --arch=x64
   ```

---

✅ You now have a **React-style, component-based desktop app** built with **Electron**.

---

