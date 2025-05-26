import React, { useState } from "react";
import { initializeApp } from "firebase/app";
import { getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword } from "firebase/auth";
import { getFirestore, doc, setDoc } from "firebase/firestore";

const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_AUTH_DOMAIN",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_STORAGE_BUCKET",
  messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
  appId: "YOUR_APP_ID"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

export default function App() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isNewUser, setIsNewUser] = useState(false);
  const [profile, setProfile] = useState({
    name: "",
    age: "",
    sex: "",
    weight: "",
    height: "",
    goal: "",
    timeframe: "",
    restrictions: ""
  });

  const handleAuth = async () => {
    try {
      let userCred;
      if (isNewUser) {
        userCred = await createUserWithEmailAndPassword(auth, email, password);
        await setDoc(doc(db, "users", userCred.user.uid), profile);
      } else {
        await signInWithEmailAndPassword(auth, email, password);
      }
      alert("Success!");
    } catch (err) {
      alert(err.message);
    }
  };

  const handleChange = (e) => {
    setProfile({ ...profile, [e.target.name]: e.target.value });
  };

  return (
    <div className="p-4 max-w-md mx-auto">
      <h1 className="text-2xl font-bold mb-4">{isNewUser ? "Sign Up" : "Sign In"}</h1>
      <input className="block mb-2 w-full" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input className="block mb-2 w-full" type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} />
      {isNewUser && (
        <div className="space-y-2">
          <input name="name" placeholder="Name" onChange={handleChange} className="block w-full" />
          <input name="age" placeholder="Age" onChange={handleChange} className="block w-full" />
          <input name="sex" placeholder="Sex" onChange={handleChange} className="block w-full" />
          <input name="weight" placeholder="Weight (kg)" onChange={handleChange} className="block w-full" />
          <input name="height" placeholder="Height (cm)" onChange={handleChange} className="block w-full" />
          <select name="goal" onChange={handleChange} className="block w-full">
            <option value="">Select Goal</option>
            <option value="bulk">Bulk</option>
            <option value="cut">Cut</option>
            <option value="maintain">Maintain</option>
          </select>
          <input name="timeframe" placeholder="Timeframe (weeks)" onChange={handleChange} className="block w-full" />
          <input name="restrictions" placeholder="Dietary Restrictions" onChange={handleChange} className="block w-full" />
        </div>
      )}
      <button onClick={handleAuth} className="mt-4 p-2 bg-blue-600 text-white w-full rounded">{isNewUser ? "Register" : "Login"}</button>
      <button onClick={() => setIsNewUser(!isNewUser)} className="mt-2 underline text-sm">
        {isNewUser ? "Already have an account? Sign in" : "New here? Create an account"}
      </button>
    </div>
  );
}
