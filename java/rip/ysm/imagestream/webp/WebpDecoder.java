package rip.ysm.imagestream.webp;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.IOException;

public class WebpDecoder {
    public BufferedImage read(byte[] data) throws IOException {
        BufferedImage image = ImageIO.read(new ByteArrayInputStream(data));
        if (image == null) throw new IOException("WebP image requires PNG preprocessing");
        return image;
    }
}
