import Foundation
import AVFoundation
import CoreMedia
@preconcurrency import ScreenCaptureKit

final class AudioStreamSink: NSObject, SCStreamOutput, SCStreamDelegate {
    private let outputFormat = AVAudioFormat(
        commonFormat: .pcmFormatFloat32,
        sampleRate: 48_000,
        channels: 1,
        interleaved: false
    )!
    private var converters: [String: AVAudioConverter] = [:]

    func stream(
        _ stream: SCStream,
        didOutputSampleBuffer sampleBuffer: CMSampleBuffer,
        of outputType: SCStreamOutputType
    ) {
        guard outputType == .audio, sampleBuffer.isValid, sampleBuffer.numSamples > 0,
              let description = sampleBuffer.formatDescription,
              let asbd = CMAudioFormatDescriptionGetStreamBasicDescription(description),
              let inputFormat = AVAudioFormat(streamDescription: asbd) else {
            return
        }

        let inputFrames = AVAudioFrameCount(sampleBuffer.numSamples)
        guard let inputBuffer = AVAudioPCMBuffer(pcmFormat: inputFormat, frameCapacity: inputFrames) else {
            return
        }
        inputBuffer.frameLength = inputFrames
        let copyStatus = CMSampleBufferCopyPCMDataIntoAudioBufferList(
            sampleBuffer,
            at: 0,
            frameCount: Int32(inputFrames),
            into: inputBuffer.mutableAudioBufferList
        )
        guard copyStatus == noErr else {
            FileHandle.standardError.write(Data("ERROR: Falha ao copiar PCM: \(copyStatus)\n".utf8))
            return
        }

        let key = "\(inputFormat.sampleRate)-\(inputFormat.channelCount)-\(inputFormat.commonFormat.rawValue)-\(inputFormat.isInterleaved)"
        let converter: AVAudioConverter
        if let existing = converters[key] {
            converter = existing
        } else if let created = AVAudioConverter(from: inputFormat, to: outputFormat) {
            converters[key] = created
            converter = created
        } else {
            FileHandle.standardError.write(Data("ERROR: Formato de áudio do sistema não suportado.\n".utf8))
            return
        }

        let ratio = outputFormat.sampleRate / inputFormat.sampleRate
        let outputFrames = AVAudioFrameCount(ceil(Double(inputFrames) * ratio)) + 8
        guard let outputBuffer = AVAudioPCMBuffer(pcmFormat: outputFormat, frameCapacity: outputFrames) else {
            return
        }

        var suppliedInput = false
        var conversionError: NSError?
        let status = converter.convert(to: outputBuffer, error: &conversionError) { _, outStatus in
            if suppliedInput {
                outStatus.pointee = .noDataNow
                return nil
            }
            suppliedInput = true
            outStatus.pointee = .haveData
            return inputBuffer
        }
        guard status != .error, conversionError == nil,
              outputBuffer.frameLength > 0,
              let channel = outputBuffer.floatChannelData?[0] else {
            if let error = conversionError {
                FileHandle.standardError.write(Data("ERROR: \(error.localizedDescription)\n".utf8))
            }
            return
        }

        let byteCount = Int(outputBuffer.frameLength) * MemoryLayout<Float>.size
        FileHandle.standardOutput.write(Data(bytes: channel, count: byteCount))
    }

    func stream(_ stream: SCStream, didStopWithError error: Error) {
        FileHandle.standardError.write(Data("ERROR: \(error.localizedDescription)\n".utf8))
        exit(2)
    }
}

@main
struct ParrotSystemAudioCapture {
    static func parentPID() -> pid_t? {
        guard let index = CommandLine.arguments.firstIndex(of: "--parent-pid"),
              CommandLine.arguments.indices.contains(index + 1),
              let value = Int32(CommandLine.arguments[index + 1]) else {
            return nil
        }
        return value
    }

    static func main() async {
        guard #available(macOS 13.0, *) else {
            FileHandle.standardError.write(Data("ERROR: O áudio do sistema requer macOS 13 ou superior.\n".utf8))
            exit(1)
        }

        do {
            let content = try await SCShareableContent.excludingDesktopWindows(
                false,
                onScreenWindowsOnly: false
            )
            guard let display = content.displays.first else {
                throw NSError(
                    domain: "ParrotSystemAudio",
                    code: 1,
                    userInfo: [NSLocalizedDescriptionKey: "Nenhuma tela disponível para capturar áudio."]
                )
            }

            let ignoredPIDs = Set([parentPID(), Optional(getpid())].compactMap { $0 })
            let excludedApps = content.applications.filter { ignoredPIDs.contains($0.processID) }
            let filter = SCContentFilter(
                display: display,
                excludingApplications: excludedApps,
                exceptingWindows: []
            )
            let configuration = SCStreamConfiguration()
            configuration.capturesAudio = true
            configuration.excludesCurrentProcessAudio = true
            configuration.sampleRate = 48_000
            configuration.channelCount = 1
            configuration.width = 2
            configuration.height = 2
            configuration.minimumFrameInterval = CMTime(value: 1, timescale: 2)
            configuration.queueDepth = 3

            let sink = AudioStreamSink()
            let stream = SCStream(filter: filter, configuration: configuration, delegate: sink)
            let queue = DispatchQueue(label: "com.davidjunior.parrot.system-audio")
            try stream.addStreamOutput(sink, type: .audio, sampleHandlerQueue: queue)
            try await stream.startCapture()
            FileHandle.standardError.write(Data("READY: ScreenCaptureKit 48000Hz mono\n".utf8))

            while true {
                try await Task.sleep(nanoseconds: 3_600_000_000_000)
            }
        } catch {
            FileHandle.standardError.write(Data("ERROR: \(error.localizedDescription)\n".utf8))
            exit(1)
        }
    }
}
