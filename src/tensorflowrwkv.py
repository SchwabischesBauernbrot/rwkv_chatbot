import tensorflow as tf


class RWKVTFLayer():
    def __init__(self, key: tf.Tensor, receptance: tf.Tensor, value: tf.Tensor, ln1w: tf.Tensor, ln1b: tf.Tensor, ln2w: tf.Tensor, ln2b: tf.Tensor, time_mix_k_ffn: tf.Tensor, time_mix_r_ffn: tf.Tensor, key_ffn: tf.Tensor, receptance_ffn: tf.Tensor, value_ffn: tf.Tensor, kktk: tf.Tensor, vvtv: tf.Tensor, rrtr: tf.Tensor, time_first: tf.Tensor, time_decay: tf.Tensor, outputvv: tf.Tensor):
        self.key: tf.Tensor = key
        self.receptance: tf.Tensor = receptance
        self.value: tf.Tensor = value

        self.ln1w: tf.Tensor = ln1w
        self.ln1b: tf.Tensor = ln1b

        self.ln2w: tf.Tensor = ln2w
        self.ln2b: tf.Tensor = ln2b

        self.time_mix_k_ffn: tf.Tensor = time_mix_k_ffn
        self.time_mix_r_ffn: tf.Tensor = time_mix_r_ffn

        self.key_ffn: tf.Tensor = key_ffn
        self.receptance_ffn: tf.Tensor = receptance_ffn
        self.value_ffn: tf.Tensor = value_ffn

        self.kktk: tf.Tensor = kktk
        self.vvtv: tf.Tensor = vvtv
        self.rrtr: tf.Tensor = rrtr

        self.time_first: tf.Tensor = time_first
        self.time_decay: tf.Tensor = time_decay

        self.outputvv: tf.Tensor = outputvv


class RWKV(tf.keras.Model):
    def __init__(self: tf.Tensor, preprocess, postprocess, layers):
        super(RWKV, self).__init__()
        self.preprocess = preprocess

        self.mylayers: list[RWKVTFLayer] = layers

        self.postprocess0 = postprocess[0]
        self.postprocess1 = postprocess[1]
        self.postprocess2 = postprocess[2]

    def layernorm(self, x, w, b):
        xee2 = x - tf.reduce_mean(x)

        x2 = tf.sqrt(tf.reduce_mean(tf.square(xee2)) + 0.000009999999747378752)

        return tf.add(tf.multiply(tf.divide(xee2,
                                            x2), w), b)

    def call(self, x, state):
        x = self.preprocess[x]

        statea, stateb, statec, stated = state

        ot = []

        for i, ilayer in enumerate(self.mylayers):
            ln1wa = ilayer.ln1w
            ln1ba = ilayer.ln1b

            ln2wa = ilayer.ln2w
            ln2ba = ilayer.ln2b
            atd = ilayer.key
            rtd = ilayer.receptance
            vtd = ilayer.value

            tmk = ilayer.time_mix_k_ffn * stated[i]
            tmr = ilayer.time_mix_r_ffn * stated[i]

            tmkw = ilayer.key_ffn
            tmrw = ilayer.receptance_ffn
            tmvw = ilayer.value_ffn

            kktk = ilayer.kktk
            vvtv = ilayer.vvtv
            rrtr = ilayer.rrtr

            time_first = ilayer.time_first
            time_decay = ilayer.time_decay

            outputvv = ilayer.outputvv

            # print("x", x.shape, "states", statea[i].shape, stateb[i].shape, statec[i].shape, stated[i].shape, "stuff", ln1wa.shape, ln1ba.shape, ln2wa.shape, ln2ba.shape, atd.shape, rtd.shape,
            #       vtd.shape, tmk.shape, tmr.shape, "tmkw", tmkw.shape, tmrw.shape, tmvw.shape, kktk.shape, vvtv.shape, rrtr.shape, time_first.shape, time_decay.shape, outputvv.shape)

            xy = self.layernorm(x, ln1wa, ln1ba)

            # print(statea[i].squeeze().shape)
            # print(xy.squeeze().shape)
            # print(kktk[i].squeeze().shape)
            # print(atd.shape)

            k = tf.exp(tf.reduce_sum(atd*(xy+kktk*statea[i]), 1))

            v = tf.reduce_sum(vtd*(xy+vvtv*statea[i]), 1)

            r = tf.exp(tf.reduce_sum(rtd*(xy+rrtr*statea[i]), 1)) + 1

            w = stateb[i] + tf.exp(time_first)*k*v
            d = statec[i]*r+tf.exp(time_first)*k*r

            mvv = tf.reduce_sum(outputvv*w/(d+0.001), 1)
            sxx = x + mvv

            aaa = xy

            bbb = stateb[i] * tf.exp(time_decay) + k * v  # ne33nd
            ccc = statec[i] * tf.exp(time_decay) + k

            # return output, outstateA, outstateB, outstateC

            xx = self.layernorm(sxx, ln2wa, ln2ba)

            # xx = torch.layer_norm(sxx, (self.sshape,),
            #                       weight=ln2wa, bias=ln2ba)

            kma = tf.reduce_sum(tmkw * (xx +
                                        tmk), 1)
            # kma[kma <= 0] = 0
            km = tf.square(tf.maximum(kma, tf.zeros_like(kma)))

            rt = tf.exp(tf.reduce_sum(tmrw*(xx + tmr), 1)) + 1

            x = sxx + tf.reduce_sum(tmvw*km, 1
                                    )/rt

            ddd = xx

            # print(aaa.shape, bbb.shape, ccc.shape, ddd.shape)

            ot = ot + [aaa, bbb, ccc, ddd]

        x = tf.reduce_sum(self.layernorm(x, self.postprocess0,
                          self.postprocess1) * self.postprocess2, 1)

        return x, [ot[::4], ot[1::4], ot[2::4], ot[3::4]]

    def reset(self):
        self.state.assign(tf.zeros((1, 1, self.embed), dtype=self.floatmode))

    def save(self, path):
        self.save_weights(path)

    def load(self, path):
        self.load_weights(path)
