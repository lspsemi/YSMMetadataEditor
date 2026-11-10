// SPDX-License-Identifier: GPL-3.0-only
package rip.ysm.imagestream.avif;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.IOException;

public class AvifDecoder {
    public BufferedImage read(byte[] data) throws IOException {
        BufferedImage image = ImageIO.read(new ByteArrayInputStream(data));
        if (image == null) throw new IOException("AVIF image requires PNG preprocessing");
        return image;
    }
}
