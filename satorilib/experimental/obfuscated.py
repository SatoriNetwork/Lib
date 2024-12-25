''' an exercise '''
import joblib
import numpy as np

class ObfuscationNetwork:
    def __init__(self, data, hidden_size=1024, lr=0.001, stop_threshold=.1):
        self.hidden_size = hidden_size
        self.lr = lr
        self.stop_threshold = stop_threshold
        self.data = data

        # Prepare data
        self.X = np.stack([self.str_to_vec(s) for s in data])
        self.Y = np.roll(self.X, shift=-1, axis=0)
        self.N, self.input_dim = self.X.shape
        self.output_dim = self.input_dim

        # Initialize model
        self.rng = np.random.default_rng(1234)
        self.model = {
            "W1": self.rng.normal(scale=0.01, size=(self.input_dim, hidden_size)),
            "b1": np.zeros(hidden_size),
            "W2": self.rng.normal(scale=0.01, size=(hidden_size, self.output_dim)),
            "b2": np.zeros(self.output_dim),
        }

        # Initialize Adam state
        self.adam_state = {
            k + "_m": np.zeros_like(self.model[k]) for k in self.model
        }
        self.adam_state.update({
            k + "_v": np.zeros_like(self.model[k]) for k in self.model
        })
        self.beta1, self.beta2, self.eps = 0.9, 0.999, 1e-8
        self.t = 0  # iteration counter

    def load(self, path:str = 'chaos_model.joblib'):
        return joblib.load(path)

    def save(self, path:str = 'chaos_model.joblib'):
        return joblib.dump(nn, path)

    def str_to_vec(self, s):
        return np.array([ord(c) for c in s], dtype=np.float32)

    def vec_to_str(self, v):
        v = np.round(v)
        v = np.clip(v, 32, 126)
        return ''.join(chr(int(x)) for x in v)

    def relu(self, x):
        return np.maximum(x, 0)

    def forward(self, x):
        z1 = x @ self.model["W1"] + self.model["b1"]
        h = self.relu(z1)
        z2 = h @ self.model["W2"] + self.model["b2"]
        return z2, (z1, h)

    def mse(self, pred, target):
        return np.mean((pred - target)**2)

    def is_close(self, pred, target, threshold=0.25):
        return np.all(np.abs(pred - target) < threshold)

    def adam_update(self, param_name, grad):
        m_key = param_name + "_m"
        v_key = param_name + "_v"
        self.adam_state[m_key] = self.beta1 * self.adam_state[m_key] + (1 - self.beta1) * grad
        self.adam_state[v_key] = self.beta2 * self.adam_state[v_key] + (1 - self.beta2) * (grad**2)
        m_hat = self.adam_state[m_key] / (1 - self.beta1**self.t)
        v_hat = self.adam_state[v_key] / (1 - self.beta2**self.t)
        self.model[param_name] -= self.lr * m_hat / (np.sqrt(v_hat) + self.eps)

    def train(self, max_epochs=50000):
        for epoch in range(max_epochs or 9999999999999999999999999999999999999):
            i = self.rng.integers(self.N)
            x_i = self.X[i:i+1]
            y_i = self.Y[i:i+1]

            preds, (z1, h) = self.forward(x_i)
            loss = self.mse(preds, y_i)

            dpred = 2.0 * (preds - y_i)
            dW2 = h.T @ dpred
            db2 = np.sum(dpred, axis=0)
            dh = dpred @ self.model["W2"].T
            dz1 = dh * (z1 > 0)
            dW1 = x_i.T @ dz1
            db1 = np.sum(dz1, axis=0)

            self.t += 1
            self.adam_update("W2", dW2)
            self.adam_update("b2", db2)
            self.adam_update("W1", dW1)
            self.adam_update("b1", db1)

            if epoch % 2000 == 0 or (max_epochs is not None and epoch == max_epochs - 1):
                all_preds, _ = self.forward(self.X)
                full_loss = self.mse(all_preds, self.Y)
                print(f"Epoch {epoch}, single-example loss={loss:.4f}, full-dataset MSE={full_loss:.4f}")
                if full_loss < self.stop_threshold or self.is_close(all_preds, self.Y):
                    print("Training stopped early; memorizations likely complete.")
                    preds_all, _ = self.forward(self.X)
                    all_match = True
                    for i, (inp, predv, truthv) in enumerate(zip(self.X, preds_all, self.Y)):
                        e = self.mse(predv, truthv)
                        print(f"Index {i}, MSE={e:.4f}")
                        # You can also print the strings if you want:
                        input_str = self.vec_to_str(inp)
                        truth_str = self.vec_to_str(truthv)
                        prediction = self.vec_to_str(predv)
                        print("   input: ", input_str)
                        print("   truth: ", truth_str)
                        print("   pred : ", prediction)
                        if prediction != truth_str:
                            all_match = False
                            break
                    if all_match:
                        print("memorizations complete.")
                        break

    def predict(self, input_str):
        inp_vec = self.str_to_vec(input_str)[None, :]
        out_vec, _ = self.forward(inp_vec)
        return self.vec_to_str(out_vec[0])

    def view(self, input_str, n=-1):
        strings = []
        string = input_str
        for _ in range(n if n > 0 else float('inf')):
            if string in strings:
                break
            strings.append(string)
            string = self.predict(string)
        return strings

def test():
    nn = ObfuscationNetwork(data=["hello", "world", "test!"], hidden_size=128)
    nn.train(max_epochs=None)
    nn.view("hello", n=5)
    # in order to obfuscate, you need a layer of training which similar
    # variations of these to chaotic outputs. exponentially increasing trainning
    model = ObfuscationNetwork([
        'MIGHAgEA',
        'MBMGByqG',
        'SM49AgEG',
        'CCqGSM49',
        'AwEHBG0w',
        'awIBAQQg',
        'zG0YRoLv',
        'e4maOyRi',
        'Y0dZfs35',
        'bDrhv5Sk',
        'UbZgFHK9',
        'AFWhRANC',
        'AAS0JHmy',
        'M/VDRrnD',
        'WLtr/naS',
        'iIC6xt9y',
        '3ARYEt/6',
        'UpgLeAbX',
        'GRKTfyIF',
        'SmVZej9i',
        '8ogkchx7',
        'S1Ms77sr',
        '2TpxCzlb'])
    model.train(max_epochs=None)
    print(model.view('MIGHAgEA', n=25))
