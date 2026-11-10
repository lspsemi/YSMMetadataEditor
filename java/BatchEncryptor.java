// SPDX-License-Identifier: GPL-3.0-only
import com.elfmcys.yesstevemodel.resource.YSMBinarySerializer;
import com.elfmcys.yesstevemodel.resource.YSMFolderDeserializer;
import com.elfmcys.yesstevemodel.resource.pojo.RawYsmModel;
import rip.ysm.algorithms.CityHash;
import rip.ysm.security.YSMByteBuf;
import rip.ysm.security.YsmCrypt;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.SecureRandom;
import java.time.Instant;
import java.nio.charset.StandardCharsets;
import java.util.HexFormat;

public final class BatchEncryptor {
    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("Usage: BatchEncryptor <model-folder> <output.ysm>");
            System.exit(2);
        }
        Path folder = Path.of(args[0]);
        Path output = Path.of(args[1]);
        if (!Files.isRegularFile(folder.resolve("ysm.json"))) {
            throw new IllegalArgumentException("Missing ysm.json: " + folder);
        }
        RawYsmModel model;
        try (YSMFolderDeserializer deserializer = new YSMFolderDeserializer(folder)) {
            model = deserializer.deserialize();
        }
        model.footer.version = 32;
        model.footer.unkInt1 = 1;
        byte[] nonce = new byte[8];
        new SecureRandom().nextBytes(nonce);
        model.footer.rand = HexFormat.of().formatHex(nonce);
        model.footer.time = Instant.now().getEpochSecond();
        model.footer.extra = "";
        model.footer.unkInt2 = 0;

        byte[] body;
        try (YSMByteBuf serialized = YSMBinarySerializer.serialize(model, 32, true)) {
            byte[] core = serialized.toArray();
            ByteBuffer wrapper = ByteBuffer.allocate(4 + core.length).order(ByteOrder.LITTLE_ENDIAN);
            wrapper.putInt(32);
            wrapper.put(core);
            body = wrapper.array();
        }
        byte[] encrypted = addParserFormatHeader(YsmCrypt.encryptYsmFile(body));
        Files.createDirectories(output.toAbsolutePath().getParent());
        Files.write(output, encrypted);
        System.out.println("Encrypted: " + folder + " -> " + output);
    }

    private static byte[] addParserFormatHeader(byte[] encrypted) {
        byte[] formatLine = "<format> 32\r\n".getBytes(StandardCharsets.UTF_8);
        int headerPrefix = 7; // UTF-8 BOM + YSGP
        if (encrypted.length < headerPrefix + 1 + 64 || encrypted[headerPrefix] != 0) {
            throw new IllegalArgumentException("Unexpected OpenYSM encrypted file header");
        }
        byte[] patched = new byte[encrypted.length + formatLine.length];
        System.arraycopy(encrypted, 0, patched, 0, headerPrefix);
        System.arraycopy(formatLine, 0, patched, headerPrefix, formatLine.length);
        int restLength = encrypted.length - headerPrefix - 8;
        System.arraycopy(encrypted, headerPrefix, patched, headerPrefix + formatLine.length, restLength);
        long hash = new CityHash().hash64WithSeed(
                patched, 0, patched.length - 8, YsmCrypt.SEED_FILE_VERIFICATION);
        ByteBuffer.wrap(patched).order(ByteOrder.LITTLE_ENDIAN).putLong(patched.length - 8, hash);
        return patched;
    }
}
